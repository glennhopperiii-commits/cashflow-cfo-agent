"""Phase 1 verification checklist for the cashflow-cfo-agent harness.

Re-runnable after any change to the data generator, engine, Monte Carlo, or
scenario logic. Verifies every control total and calibrated demo target
without touching the Anthropic API (no key needed, costs nothing).

Run from the repo root:  python3 tests/phase1_checklist.py
Exits nonzero if any check fails.
"""

import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cashflow_harness import tools  # noqa: E402
from cashflow_harness.config import DATA_DIR  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def main():
    # 1. Data reconciles to the documented control totals
    ar = tools.load_receivables()
    ap = tools.load_payables_and_fixed()
    vantage = next(c for c in ar["customers"] if c["customer"] == "Vantage Aerospace")
    check("AR total = $19.3M", ar["total_open_ar"] == 19_300_000, f"${ar['total_open_ar']:,}")
    check("~120 invoices", 110 <= ar["invoice_count"] <= 130, str(ar["invoice_count"]))
    check("Vantage = $4.2M ~22%",
          vantage["open_ar"] == 4_200_000 and 0.20 <= vantage["share_of_ar"] <= 0.23,
          f"${vantage['open_ar']:,} ({vantage['share_of_ar']:.1%})")
    check("Top 5 ~60% of AR", 0.58 <= ar["top5_concentration"] <= 0.62, f"{ar['top5_concentration']:.1%}")
    check("AP total = $8.7M / ~90 bills",
          ap["total_open_ap"] == 8_700_000 and ap["ap_bill_count"] == 90,
          f"${ap['total_open_ap']:,} / {ap['ap_bill_count']}")

    expected_weeks = {"insurance": 5, "capex": 6, "acquisition": 9, "tax": 10}
    one_timer_ok = all(
        any(i["week"] == wk and i["category"] == cat for i in ap["one_time_items"])
        for cat, wk in expected_weeks.items()
    ) and sum(i["amount"] for i in ap["one_time_items"] if i["category"] == "debt service") == 2_200_000 \
      and all(i["week"] == 13 for i in ap["one_time_items"] if i["category"] == "debt service")
    check("Fixed one-timers in right weeks (5/6/9/10/13)", one_timer_ok)

    with open(DATA_DIR / "fixed_schedule.csv") as f:
        fixed_rows = list(csv.DictReader(f))
    payroll_weeks = sorted({int(r["week"]) for r in fixed_rows if r["category"] == "payroll"})
    check("Biweekly payroll weeks 1,3,...,13", payroll_weeks == [1, 3, 5, 7, 9, 11, 13], str(payroll_weeks))

    # 2. Deterministic demo targets
    det = tools.build_deterministic_forecast()
    check("Trough ~$1.6M in week 8",
          det["trough_week"] == 8 and 1_500_000 <= det["trough_cash"] <= 1_700_000,
          f"${det['trough_cash']:,.0f} wk {det['trough_week']}")
    check("W13 headroom ~$0.6M", 500_000 <= det["covenant_headroom"] <= 750_000,
          f"${det['covenant_headroom']:,.0f}")
    check("Covenant passes deterministically", det["covenant_pass"])
    w7 = det["weeks"][6]
    check("Week 7 revolver draw before the trough", w7["revolver_draw"] > 0, f"${w7['revolver_draw']:,.0f}")

    # 3. Monte Carlo targets and reproducibility
    mc1 = tools.run_monte_carlo()
    mc2 = tools.run_monte_carlo()
    check("Breach probability 18-22%", 0.18 <= mc1["p_covenant_breach"] <= 0.22,
          f"{mc1['p_covenant_breach']:.1%}")
    check("Seeded MC reproducible", mc1 == mc2)
    fan_ok = all(p10 <= p50 <= p90 for p10, p50, p90 in
                 zip(mc1["ending_cash_p10"], mc1["ending_cash_p50"], mc1["ending_cash_p90"]))
    check("Coherent P10<=P50<=P90 fan", fan_ok)
    check("P10 breaches at W13, P50 passes",
          mc1["test_week_liquidity_p10"] < 4_000_000 < mc1["test_week_liquidity_p50"],
          f"P10 ${mc1['test_week_liquidity_p10']:,} / P50 ${mc1['test_week_liquidity_p50']:,}")

    # 4. Scenario levers behave as designed
    defer = tools.run_scenario(scenario_type="defer_item", item="capex deposit", to_week=14)
    acc = tools.run_scenario(scenario_type="accelerate_collection", customer="Vantage Aerospace", days=45)
    check("Defer capex past test raises headroom & cuts breach",
          defer["result"]["delta_covenant_headroom"] > 0 and defer["result"]["delta_p_breach"] < 0,
          f"+${defer['result']['delta_covenant_headroom']:,.0f}, {defer['result']['delta_p_breach']:+.1%}")
    check("Accelerate Vantage raises headroom & cuts breach",
          acc["result"]["delta_covenant_headroom"] > 0 and acc["result"]["delta_p_breach"] < 0,
          f"+${acc['result']['delta_covenant_headroom']:,.0f}, {acc['result']['delta_p_breach']:+.1%}")

    # 5. Trailing variance story
    var = tools.compute_variance()
    check("Trailing miss ~6% under forecast", -0.065 <= var["variance_pct_of_forecast"] <= -0.055,
          f"{var['variance_pct_of_forecast']:.1%}")
    check("Miss attributed to Vantage timing", var["attribution"]["vantage_share_of_miss"] >= 0.75,
          f"{var['attribution']['vantage_share_of_miss']:.0%}")

    # 6. Frozen dataset regenerates byte-identically
    import hashlib

    def dir_hash():
        h = hashlib.md5()
        for p in sorted(DATA_DIR.glob("*")):
            if p.is_file():
                h.update(p.read_bytes())
        return h.hexdigest()

    before = dir_hash()
    from cashflow_harness import data_gen
    data_gen.generate_all()
    check("Dataset regenerates byte-identically (frozen seed + anchor)", dir_hash() == before)

    # 7. No hardcoded API key anywhere tracked
    grep = subprocess.run(
        ["git", "grep", "-l", "sk-ant"], cwd=ROOT, capture_output=True, text=True)
    hits = [l for l in grep.stdout.splitlines() if "your-key-here" not in l]
    check("No API key in tracked files", len(hits) == 0, f"{len(hits)} hits")

    print()
    failed = [r for r in results if not r[1]]
    print(f"{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
