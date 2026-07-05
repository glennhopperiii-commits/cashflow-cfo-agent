"""Probabilistic layer: Monte Carlo over collection timing and sales volume.

Each iteration resamples when customers actually pay and how much the ramp
actually bills, rebuilds the weekly flows, and re-runs the deterministic
engine. The engine is pure, so a thousand replays are just a thousand
function calls.

Sampling model:
  - Collection timing. Each customer's days-to-pay gets one systematic shift
    per iteration (a customer that pays late pays late on every invoice),
    plus idiosyncratic noise per invoice. The two components split the
    customer's observed sigma so total variance matches history.
  - Sales volume. Each week's new billings draw around the forecast with
    that week's sigma. Collections keep the blended lag; the lag itself also
    gets a small systematic shift per iteration, because the ramp billings
    collecting near the week-13 boundary are exactly where timing risk turns
    into covenant risk.

Reported "below floor" probability means ending cash below the operating
floor even after revolver draws, i.e. the draw needed to restore the floor
exceeded remaining availability. That is the treasury definition of trouble:
the floor cannot be bought back.
"""

from datetime import date, timedelta

import numpy as np

from . import engine

SYSTEMATIC_SHARE = 0.6      # share of pay-time sigma that is per-customer, per-iteration
BASE_LAG_SIGMA_DAYS = 3     # systematic shift on the blended new-billings lag
WEEK_LAG_SIGMA_DAYS = 4     # additional per-billing-week lag noise


def run_monte_carlo(
    invoices: list[dict],
    bills: list[dict],
    fixed_items: list[dict],
    sales_forecast: list[dict],
    facility: dict,
    iterations: int = 1_000,
    seed: int = 42,
) -> dict:
    rng = np.random.default_rng(seed)
    week1_monday = date.fromisoformat(facility["week1_monday"])
    num_weeks = int(facility.get("num_weeks", 13))
    floor = facility["operating_cash_floor"]
    threshold = facility["covenant"]["threshold"]

    # Disbursements do not vary across iterations.
    ap_items = [{"date": b["due_date"], "amount": b["amount"]} for b in bills]
    disbursements = engine.bucket_flows(ap_items, week1_monday, num_weeks)
    fixed = engine.bucket_flows(fixed_items, week1_monday, num_weeks)
    disbursements = [d + f for d, f in zip(disbursements, fixed)]

    customers = sorted({inv["customer"] for inv in invoices})
    cust_sigma = {
        c: max(inv["customer_pay_sigma"] for inv in invoices if inv["customer"] == c)
        for c in customers
    }

    idio_share = (1 - SYSTEMATIC_SHARE**2) ** 0.5

    ending_cash = np.zeros((iterations, num_weeks))
    liquidity = np.zeros((iterations, num_weeks))
    troughs = np.zeros(iterations)
    trough_weeks = np.zeros(iterations, dtype=int)
    below_floor = np.zeros(iterations, dtype=bool)
    breach = np.zeros(iterations, dtype=bool)

    for it in range(iterations):
        shifts = {
            c: rng.normal(0.0, SYSTEMATIC_SHARE * cust_sigma[c]) for c in customers
        }
        base_lag_shift = rng.normal(0.0, BASE_LAG_SIGMA_DAYS)

        receipts = [0.0] * num_weeks
        for inv in invoices:
            days = (
                inv["customer_days_to_pay"]
                + shifts[inv["customer"]]
                + rng.normal(0.0, idio_share * inv["customer_pay_sigma"])
            )
            pay = date.fromisoformat(inv["invoice_date"]) + timedelta(days=int(round(max(days, 1))))
            w = engine.date_to_week(pay, week1_monday, num_weeks)
            if w <= num_weeks:
                receipts[w - 1] += inv["amount"]

        vantage_shift = shifts.get("Vantage Aerospace", 0.0)
        for row in sales_forecast:
            billings = max(rng.normal(row["billings"], row["sigma"]), 0.0)
            week_start = date.fromisoformat(str(row["week_start"]))
            week_lag_noise = rng.normal(0.0, WEEK_LAG_SIGMA_DAYS)
            for amount, lag, source in engine.split_sales_row(dict(row, billings=billings)):
                if amount <= 0:
                    continue
                shift = vantage_shift if source == "vantage" else base_lag_shift + week_lag_noise
                collect = week_start + timedelta(days=int(round(lag + shift)))
                w = engine.date_to_week(collect, week1_monday, num_weeks)
                if w <= num_weeks:
                    receipts[w - 1] += amount

        result = engine.run_forecast(
            beginning_cash=facility["beginning_cash"],
            revolver_limit=facility["revolver_limit"],
            revolver_drawn=facility["revolver_drawn"],
            operating_floor=floor,
            covenant_threshold=threshold,
            weekly_receipts=receipts,
            weekly_disbursements=disbursements,
            sweep_buffer=facility.get("sweep_buffer", 500_000),
            draw_increment=facility.get("draw_increment", 250_000),
            covenant_test_week=facility["covenant"]["test_week"],
        )

        weeks = result["weeks"]
        ending_cash[it] = [w["ending_cash"] for w in weeks]
        liquidity[it] = [w["covenant_liquidity"] for w in weeks]
        troughs[it] = result["trough_cash"]
        trough_weeks[it] = result["trough_week"]
        below_floor[it] = any(w["ending_cash"] < floor - 0.01 for w in weeks)
        breach[it] = not result["covenant_pass"]

    def pct(arr, q):
        return np.percentile(arr, q, axis=0)

    test_ix = facility["covenant"]["test_week"] - 1
    w13_liq = liquidity[:, test_ix]

    return {
        "iterations": iterations,
        "seed": seed,
        "weeks": list(range(1, num_weeks + 1)),
        "ending_cash_p10": [round(x) for x in pct(ending_cash, 10)],
        "ending_cash_p50": [round(x) for x in pct(ending_cash, 50)],
        "ending_cash_p90": [round(x) for x in pct(ending_cash, 90)],
        "liquidity_p10": [round(x) for x in pct(liquidity, 10)],
        "liquidity_p50": [round(x) for x in pct(liquidity, 50)],
        "liquidity_p90": [round(x) for x in pct(liquidity, 90)],
        "trough_cash_p10": round(float(np.percentile(troughs, 10))),
        "trough_cash_p50": round(float(np.percentile(troughs, 50))),
        "trough_cash_p90": round(float(np.percentile(troughs, 90))),
        "trough_week_mode": int(np.bincount(trough_weeks).argmax()),
        "test_week": facility["covenant"]["test_week"],
        "test_week_liquidity_p10": round(float(np.percentile(w13_liq, 10))),
        "test_week_liquidity_p50": round(float(np.percentile(w13_liq, 50))),
        "test_week_liquidity_p90": round(float(np.percentile(w13_liq, 90))),
        "covenant_threshold": threshold,
        "operating_floor": floor,
        "p_below_floor_any_week": round(float(below_floor.mean()), 4),
        "p_covenant_breach": round(float(breach.mean()), 4),
    }
