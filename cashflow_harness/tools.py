"""Tool implementations for the Cascade Precision cash flow agent.

Every tool is a plain, importable Python function. The Phase 1 notebook and
the Phase 2 FastAPI server call these exact functions; if a number ever
differs between the two, the wrapper is wrong, not the engine.

Data-reading tools return structured results. Computation tools call the
deterministic engine and the Monte Carlo layer. Pass-through tools
(draft_cash_narrative) validate the agent's structured input and return a
confirmation so the payload is captured for the audit log.
"""

import copy
import csv
import json
from collections import defaultdict
from datetime import date, timedelta

from . import engine, montecarlo
from .config import DATA_DIR, MC_ITERATIONS, MC_SEED, OUTPUT_DIR

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def _load_facility() -> dict:
    with open(DATA_DIR / "facility_terms.json") as f:
        return json.load(f)


def _load_invoices() -> list[dict]:
    with open(DATA_DIR / "ar_open_invoices.json") as f:
        return json.load(f)


def _load_bills() -> list[dict]:
    with open(DATA_DIR / "ap_open_bills.json") as f:
        return json.load(f)


def _load_fixed() -> list[dict]:
    with open(DATA_DIR / "fixed_schedule.csv") as f:
        return [
            dict(r, week=int(r["week"]), amount=float(r["amount"]),
                 discretionary=r["discretionary"] == "True")
            for r in csv.DictReader(f)
        ]


def _load_sales() -> list[dict]:
    with open(DATA_DIR / "sales_forecast.csv") as f:
        return [
            dict(r, week=int(r["week"]), billings=float(r["billings"]),
                 sigma=float(r["sigma"]), base_lag_days=float(r["base_lag_days"]),
                 vantage_share=float(r["vantage_share"]),
                 vantage_lag_days=float(r["vantage_lag_days"]))
            for r in csv.DictReader(f)
        ]


def _load_history() -> list[dict]:
    with open(DATA_DIR / "historical_actuals.csv") as f:
        return [
            {k: (v if k == "week_ending" else float(v)) for k, v in r.items()}
            for r in csv.DictReader(f)
        ]


def _week1(facility: dict) -> date:
    return date.fromisoformat(facility["week1_monday"])


def _run_deterministic(facility, invoices, bills, fixed, sales) -> dict:
    receipts, disb = engine.build_weekly_flows(
        invoices, bills, fixed, sales, _week1(facility), facility["num_weeks"]
    )
    return engine.run_forecast(
        beginning_cash=facility["beginning_cash"],
        revolver_limit=facility["revolver_limit"],
        revolver_drawn=facility["revolver_drawn"],
        operating_floor=facility["operating_cash_floor"],
        covenant_threshold=facility["covenant"]["threshold"],
        weekly_receipts=receipts,
        weekly_disbursements=disb,
        sweep_buffer=facility["sweep_buffer"],
        draw_increment=facility["draw_increment"],
        covenant_test_week=facility["covenant"]["test_week"],
    )


# ---------------------------------------------------------------------------
# Tools 1-3: load the position
# ---------------------------------------------------------------------------


def load_facility_and_position() -> dict:
    facility = _load_facility()
    availability = facility["revolver_limit"] - facility["revolver_drawn"]
    return {
        "company": facility["company"],
        "as_of_close": facility["as_of_close"],
        "week1_monday": facility["week1_monday"],
        "horizon_weeks": facility["num_weeks"],
        "beginning_cash": facility["beginning_cash"],
        "revolver": {
            "limit": facility["revolver_limit"],
            "drawn": facility["revolver_drawn"],
            "availability": availability,
        },
        "beginning_liquidity": facility["beginning_cash"] + availability,
        "operating_cash_floor": facility["operating_cash_floor"],
        "sweep_buffer": facility["sweep_buffer"],
        "draw_increment": facility["draw_increment"],
        "covenant": facility["covenant"],
        "term_loan": facility["term_loan"],
    }


def load_receivables() -> dict:
    facility = _load_facility()
    invoices = _load_invoices()
    week1 = _week1(facility)
    total = sum(i["amount"] for i in invoices)

    by_customer: dict[str, dict] = {}
    for inv in invoices:
        c = by_customer.setdefault(inv["customer"], {
            "customer": inv["customer"],
            "segment": inv["segment"],
            "terms": inv["terms"],
            "days_to_pay": inv["customer_days_to_pay"],
            "pay_sigma": inv["customer_pay_sigma"],
            "open_ar": 0,
            "invoice_count": 0,
        })
        c["open_ar"] += inv["amount"]
        c["invoice_count"] += 1

    customers = sorted(by_customer.values(), key=lambda c: -c["open_ar"])
    for c in customers:
        c["share_of_ar"] = round(c["open_ar"] / total, 4)
        terms_days = int(c["terms"].split()[-1])
        c["stretch_days_vs_terms"] = round(c["days_to_pay"] - terms_days, 1)
        c["term_stretch_flag"] = c["stretch_days_vs_terms"] >= 15

    expected_by_week = defaultdict(float)
    for inv in invoices:
        w = engine.date_to_week(engine.expected_pay_date(inv), week1, facility["num_weeks"])
        expected_by_week["beyond_horizon" if w > facility["num_weeks"] else f"week_{w}"] += inv["amount"]

    top_invoices = sorted(invoices, key=lambda i: -i["amount"])[:8]
    return {
        "total_open_ar": total,
        "invoice_count": len(invoices),
        "customers": customers,
        "top5_concentration": round(sum(c["open_ar"] for c in customers[:5]) / total, 4),
        "flagged_term_stretch": [c["customer"] for c in customers if c["term_stretch_flag"]],
        "largest_open_invoices": [
            {k: inv[k] for k in ("invoice_id", "customer", "amount", "invoice_date",
                                 "due_date", "terms", "memo")}
            for inv in top_invoices
        ],
        "expected_collections_by_week": {
            k: round(v) for k, v in sorted(expected_by_week.items())
        },
        "note": "Expected collection weeks use observed customer payment behavior "
                "(days to pay), not stated terms.",
    }


def load_payables_and_fixed() -> dict:
    facility = _load_facility()
    bills = _load_bills()
    fixed = _load_fixed()
    week1 = _week1(facility)
    num_weeks = facility["num_weeks"]

    ap_by_week = defaultdict(float)
    for b in bills:
        w = engine.date_to_week(date.fromisoformat(b["due_date"]), week1, num_weeks)
        if w <= num_weeks:
            ap_by_week[w] += b["amount"]

    fixed_by_week_cat = defaultdict(lambda: defaultdict(float))
    for r in fixed:
        fixed_by_week_cat[r["week"]][r["category"]] += r["amount"]

    weekly = []
    for w in range(1, num_weeks + 1):
        cats = dict(fixed_by_week_cat.get(w, {}))
        row = {"week": w, "ap_due": round(ap_by_week.get(w, 0))}
        row.update({k.replace(" ", "_"): round(v) for k, v in sorted(cats.items())})
        row["total"] = round(ap_by_week.get(w, 0) + sum(cats.values()))
        weekly.append(row)

    discretionary = [
        {"source": "fixed_schedule", "week": r["week"], "item": r["item"], "amount": r["amount"]}
        for r in fixed if r["discretionary"]
    ] + [
        {"source": "open_ap", "week": engine.date_to_week(date.fromisoformat(b["due_date"]), week1, num_weeks),
         "item": f'{b["vendor"]}: {b["memo"] or b["category"]}', "amount": b["amount"]}
        for b in bills if b["discretionary"]
    ]

    one_timers = [
        {"week": r["week"], "item": r["item"], "category": r["category"], "amount": r["amount"]}
        for r in fixed
        if r["category"] in ("insurance", "capex", "acquisition", "tax", "debt service")
    ]

    return {
        "total_open_ap": sum(b["amount"] for b in bills),
        "ap_bill_count": len(bills),
        "weekly_disbursement_schedule": weekly,
        "one_time_items": one_timers,
        "discretionary_items": discretionary,
        "note": "AP is heaviest in weeks 3-7 from aerospace ramp material buys. "
                "Forecast material purchases (Net 30 on new ramp POs) continue "
                "through week 13.",
    }


# ---------------------------------------------------------------------------
# Tools 4-5: the engines
# ---------------------------------------------------------------------------


def build_deterministic_forecast() -> dict:
    facility = _load_facility()
    result = _run_deterministic(facility, _load_invoices(), _load_bills(), _load_fixed(), _load_sales())
    result["note"] = (
        "Single-point roll-forward using observed customer payment behavior. "
        "Revolver auto-draws in increments to defend the operating floor; "
        "excess cash above floor + buffer sweeps the revolver down."
    )
    return result


def run_monte_carlo(iterations: int | None = None, seed: int | None = None) -> dict:
    facility = _load_facility()
    return montecarlo.run_monte_carlo(
        _load_invoices(), _load_bills(), _load_fixed(), _load_sales(), facility,
        iterations=iterations or MC_ITERATIONS,
        seed=seed if seed is not None else MC_SEED,
    )


# ---------------------------------------------------------------------------
# Tool 6: scenarios
# ---------------------------------------------------------------------------


def _apply_scenario(scenario: dict, invoices, bills, fixed, sales) -> tuple[list, list, list, list]:
    """Return transformed copies of the four flow inputs for one scenario."""
    invoices = copy.deepcopy(invoices)
    bills = copy.deepcopy(bills)
    fixed = copy.deepcopy(fixed)
    sales = copy.deepcopy(sales)
    stype = scenario["scenario_type"]

    if stype == "slip_collections":
        customer = scenario.get("customer")
        days = float(scenario["days"])
        for inv in invoices:
            if customer is None or inv["customer"] == customer:
                inv["customer_days_to_pay"] += days
        for row in sales:
            if customer is None:
                row["base_lag_days"] += days
                row["vantage_lag_days"] += days
            elif customer == "Vantage Aerospace":
                row["vantage_lag_days"] += days

    elif stype == "accelerate_collection":
        customer = scenario["customer"]
        to_days = float(scenario["days"])
        for inv in invoices:
            if inv["customer"] == customer:
                inv["customer_days_to_pay"] = to_days
                inv["customer_pay_sigma"] = min(inv["customer_pay_sigma"], 3.0)
        if customer == "Vantage Aerospace":
            for row in sales:
                row["vantage_lag_days"] = to_days

    elif stype == "defer_item":
        query = scenario["item"].lower()
        to_week = int(scenario["to_week"])
        facility = _load_facility()
        week1 = _week1(facility)
        moved = False
        for r in fixed:
            if query in r["item"].lower():
                r["week"] = to_week
                r["date"] = (week1 + timedelta(days=(to_week - 1) * 7 + 2)).isoformat()
                moved = True
        for b in bills:
            if query in b["vendor"].lower() or query in (b.get("memo") or "").lower():
                b["due_date"] = (week1 + timedelta(days=(to_week - 1) * 7 + 2)).isoformat()
                moved = True
        if not moved:
            raise ValueError(f"No fixed-schedule item or bill matches '{scenario['item']}'")

    elif stype == "sales_change":
        factor = 1 + float(scenario["pct"]) / 100
        for row in sales:
            row["billings"] *= factor
            row["sigma"] *= factor

    elif stype == "stretch_ap":
        days = int(scenario["days"])
        for b in bills:
            b["due_date"] = (date.fromisoformat(b["due_date"]) + timedelta(days=days)).isoformat()

    else:
        raise ValueError(f"Unknown scenario_type: {stype}")

    return invoices, bills, fixed, sales


def _evaluate(facility, invoices, bills, fixed, sales, mc_seed=MC_SEED) -> dict:
    det = _run_deterministic(facility, invoices, bills, fixed, sales)
    mc = montecarlo.run_monte_carlo(
        invoices, bills, fixed, sales, facility, iterations=MC_ITERATIONS, seed=mc_seed
    )
    return {
        "trough_week": det["trough_week"],
        "trough_cash": det["trough_cash"],
        "test_week_liquidity": det["test_week_liquidity"],
        "covenant_headroom": det["covenant_headroom"],
        "p_covenant_breach": mc["p_covenant_breach"],
    }


DRIVER_SWEEP = [
    {"label": "Vantage pays 10 days later", "scenario_type": "slip_collections",
     "customer": "Vantage Aerospace", "days": 10},
    {"label": "Vantage accelerated to Net 45 terms", "scenario_type": "accelerate_collection",
     "customer": "Vantage Aerospace", "days": 45},
    {"label": "All customers pay 7 days later", "scenario_type": "slip_collections", "days": 7},
    {"label": "Sales 10% below forecast", "scenario_type": "sales_change", "pct": -10},
    {"label": "Sales 10% above forecast", "scenario_type": "sales_change", "pct": 10},
    {"label": "Defer capex deposit 2 weeks (wk 6 to wk 8)", "scenario_type": "defer_item",
     "item": "capex deposit", "to_week": 8},
    {"label": "Defer capex deposit past quarter end (wk 14)", "scenario_type": "defer_item",
     "item": "capex deposit", "to_week": 14},
    {"label": "Stretch all AP 7 days", "scenario_type": "stretch_ap", "days": 7},
]


def run_scenario(scenario_type: str, customer: str | None = None, days: float | None = None,
                 pct: float | None = None, item: str | None = None,
                 to_week: int | None = None) -> dict:
    """Run one what-if, or the full driver sweep when scenario_type='driver_sweep'."""
    facility = _load_facility()
    base_inputs = (_load_invoices(), _load_bills(), _load_fixed(), _load_sales())
    baseline = _evaluate(facility, *base_inputs)

    def run_one(spec: dict) -> dict:
        transformed = _apply_scenario(spec, *base_inputs)
        result = _evaluate(facility, *transformed)
        result["delta_covenant_headroom"] = round(result["covenant_headroom"] - baseline["covenant_headroom"], 2)
        result["delta_trough_cash"] = round(result["trough_cash"] - baseline["trough_cash"], 2)
        result["delta_p_breach"] = round(result["p_covenant_breach"] - baseline["p_covenant_breach"], 4)
        return result

    if scenario_type == "driver_sweep":
        results = []
        for spec in DRIVER_SWEEP:
            r = run_one(spec)
            r["label"] = spec["label"]
            results.append(r)
        results.sort(key=lambda r: -abs(r["delta_covenant_headroom"]))
        return {
            "baseline": baseline,
            "sweep": results,
            "note": "Sweep ranked by absolute impact on week-13 covenant headroom. "
                    "Moves inside the quarter shift the trough and breach odds; only "
                    "flows crossing the week-13 boundary move deterministic headroom.",
        }

    spec = {"scenario_type": scenario_type, "customer": customer, "days": days,
            "pct": pct, "item": item, "to_week": to_week}
    result = run_one(spec)
    return {"baseline": baseline, "scenario": spec, "result": result}


# ---------------------------------------------------------------------------
# Tool 7: trailing variance
# ---------------------------------------------------------------------------


def compute_variance() -> dict:
    history = _load_history()
    fc_total = sum(r["forecast_collections"] for r in history)
    ac_total = sum(r["actual_collections"] for r in history)
    miss = ac_total - fc_total

    vantage_miss = sum(r["actual_vantage"] - r["forecast_vantage"] for r in history)
    other_miss = miss - vantage_miss

    weekly = []
    for r in history:
        weekly.append({
            "week_ending": r["week_ending"],
            "forecast_collections": round(r["forecast_collections"]),
            "actual_collections": round(r["actual_collections"]),
            "variance": round(r["actual_collections"] - r["forecast_collections"]),
            "vantage_variance": round(r["actual_vantage"] - r["forecast_vantage"]),
            "other_variance": round((r["actual_collections"] - r["forecast_collections"])
                                    - (r["actual_vantage"] - r["forecast_vantage"])),
            "actual_disbursements": round(r["actual_disbursements"]),
            "actual_ending_cash": round(r["actual_ending_cash"]),
        })

    return {
        "trailing_weeks": len(history),
        "forecast_collections_total": round(fc_total),
        "actual_collections_total": round(ac_total),
        "total_variance": round(miss),
        "variance_pct_of_forecast": round(miss / fc_total, 4),
        "attribution": {
            "vantage_timing": round(vantage_miss),
            "all_other": round(other_miss),
            "vantage_share_of_miss": round(vantage_miss / miss, 4) if miss else 0,
        },
        "weekly_bridge": weekly,
        "note": "Timing vs volume: the Vantage variance is a slipped invoice that "
                "remains fully collectible (timing). The residual spread across "
                "other customers nets small and reads as normal volume noise.",
    }


# ---------------------------------------------------------------------------
# Tools 8-10: narrative, review gate, audit output
# ---------------------------------------------------------------------------


def draft_cash_narrative(sections: list[dict], recommended_action: dict) -> dict:
    """Pass-through: validate and confirm storage of the structured narrative."""
    required = {"title", "content", "confidence"}
    for s in sections:
        missing = required - set(s)
        if missing:
            raise ValueError(f"Narrative section missing fields: {missing}")
    if not {"action", "rationale"} <= set(recommended_action):
        raise ValueError("recommended_action needs 'action' and 'rationale'")
    return {
        "status": "stored",
        "section_count": len(sections),
        "section_titles": [s["title"] for s in sections],
        "recommended_action": recommended_action.get("action", ""),
    }


def submit_for_review(message: str) -> dict:
    # CLI/default mode auto-approves. The agent loop intercepts this tool and
    # routes it through the review-gate callback (notebook prompt or Phase 2
    # WebSocket gate) when one is provided.
    return {
        "status": "auto_approved",
        "message": "No review handler attached: all sections auto-approved.",
    }


def log_output(final_sections: list[dict], recommended_action_disposition: dict,
               summary: str) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # final_report.json, not audit_log.json: the AuditLogger owns audit_log.json
    # and would overwrite this at the end of the run.
    path = OUTPUT_DIR / "final_report.json"
    with open(path, "w") as f:
        json.dump({
            "summary": summary,
            "final_sections": final_sections,
            "recommended_action_disposition": recommended_action_disposition,
            "section_count": len(final_sections),
        }, f, indent=2)
    return {"status": "written", "path": str(path), "entry_count": len(final_sections)}


TOOL_FUNCTIONS = {
    "load_facility_and_position": load_facility_and_position,
    "load_receivables": load_receivables,
    "load_payables_and_fixed": load_payables_and_fixed,
    "build_deterministic_forecast": build_deterministic_forecast,
    "run_monte_carlo": run_monte_carlo,
    "run_scenario": run_scenario,
    "compute_variance": compute_variance,
    "draft_cash_narrative": draft_cash_narrative,
    "submit_for_review": submit_for_review,
    "log_output": log_output,
}


def execute_tool(tool_name: str, tool_input: dict) -> dict:
    fn = TOOL_FUNCTIONS.get(tool_name)
    if fn is None:
        return {"error": f"Unknown tool: {tool_name}"}
    try:
        return fn(**tool_input)
    except (TypeError, ValueError, KeyError) as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
