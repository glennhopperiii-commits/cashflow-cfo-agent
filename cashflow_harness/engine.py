"""Deterministic 13-week cash roll-forward with revolver mechanics.

Everything in this module is a pure function of its inputs. No file I/O, no
global state, no randomness. The Monte Carlo layer calls run_forecast()
thousands of times with resampled flows; it must stay side-effect free.

Week convention: weeks are indexed 1..num_weeks. Week 1 begins the Monday
after the latest Friday close. Dates are ISO strings ("YYYY-MM-DD");
date_to_week() maps a date onto the week grid.
"""

import math
from datetime import date, timedelta


def week_starts(week1_monday: date, num_weeks: int = 13) -> list[date]:
    """The Monday that opens each week, weeks 1..num_weeks."""
    return [week1_monday + timedelta(weeks=i) for i in range(num_weeks)]


def date_to_week(d: date, week1_monday: date, num_weeks: int = 13) -> int:
    """Map a date to a week index 1..num_weeks.

    Dates before the horizon clamp to week 1 (an overdue receipt or payment
    lands in the first week). Dates past the horizon return num_weeks + 1 so
    the caller can drop them from the 13-week view.
    """
    offset = (d - week1_monday).days
    if offset < 0:
        return 1
    week = offset // 7 + 1
    return week if week <= num_weeks else num_weeks + 1


def bucket_flows(
    items: list[dict],
    week1_monday: date,
    num_weeks: int = 13,
    date_key: str = "date",
    amount_key: str = "amount",
) -> list[float]:
    """Sum item amounts into weekly buckets. Returns a list of num_weeks floats.

    Items dated past the horizon fall out of the window (they are tail
    collections or payments beyond week 13).
    """
    weekly = [0.0] * num_weeks
    for item in items:
        d = item[date_key]
        if isinstance(d, str):
            d = date.fromisoformat(d)
        w = date_to_week(d, week1_monday, num_weeks)
        if w <= num_weeks:
            weekly[w - 1] += float(item[amount_key])
    return weekly


def run_forecast(
    beginning_cash: float,
    revolver_limit: float,
    revolver_drawn: float,
    operating_floor: float,
    covenant_threshold: float,
    weekly_receipts: list[float],
    weekly_disbursements: list[float],
    sweep_buffer: float = 500_000,
    draw_increment: float = 250_000,
    covenant_test_week: int = 13,
) -> dict:
    """Roll cash forward week by week and apply revolver mechanics.

    Per week: beginning cash + receipts - disbursements = pre-revolver cash.
    If pre-revolver cash falls below the operating floor, auto-draw on the
    revolver (rounded up to draw_increment, capped at availability) to restore
    the floor. If cash sits above floor + sweep_buffer and the revolver is
    drawn, sweep the excess to pay it down.

    Covenant liquidity is ending cash plus undrawn availability, tested at
    covenant_test_week.
    """
    num_weeks = len(weekly_receipts)
    assert len(weekly_disbursements) == num_weeks

    cash = float(beginning_cash)
    revolver = float(revolver_drawn)
    weeks = []

    for i in range(num_weeks):
        receipts = float(weekly_receipts[i])
        disbursements = float(weekly_disbursements[i])
        pre_revolver = cash + receipts - disbursements

        draw = 0.0
        paydown = 0.0
        availability = revolver_limit - revolver

        if pre_revolver < operating_floor:
            shortfall = operating_floor - pre_revolver
            draw = math.ceil(shortfall / draw_increment) * draw_increment
            draw = min(draw, availability)
        elif pre_revolver > operating_floor + sweep_buffer and revolver > 0:
            paydown = min(revolver, pre_revolver - (operating_floor + sweep_buffer))

        revolver = revolver + draw - paydown
        ending_cash = pre_revolver + draw - paydown
        availability = revolver_limit - revolver
        liquidity = ending_cash + availability

        weeks.append({
            "week": i + 1,
            "receipts": round(receipts, 2),
            "disbursements": round(disbursements, 2),
            "net_flow": round(receipts - disbursements, 2),
            "pre_revolver_cash": round(pre_revolver, 2),
            "revolver_draw": round(draw, 2),
            "revolver_paydown": round(paydown, 2),
            "revolver_balance": round(revolver, 2),
            "availability": round(availability, 2),
            "ending_cash": round(ending_cash, 2),
            "covenant_liquidity": round(liquidity, 2),
        })

        cash = ending_cash

    trough = min(weeks, key=lambda w: w["ending_cash"])
    test_week = weeks[covenant_test_week - 1]
    headroom = test_week["covenant_liquidity"] - covenant_threshold

    return {
        "weeks": weeks,
        "trough_week": trough["week"],
        "trough_cash": trough["ending_cash"],
        "min_covenant_liquidity": min(w["covenant_liquidity"] for w in weeks),
        "covenant_test_week": covenant_test_week,
        "covenant_threshold": covenant_threshold,
        "test_week_liquidity": test_week["covenant_liquidity"],
        "covenant_headroom": round(headroom, 2),
        "covenant_pass": headroom >= 0,
        "below_floor_any_week": any(
            w["pre_revolver_cash"] < operating_floor for w in weeks
        ),
        "total_revolver_draws": round(sum(w["revolver_draw"] for w in weeks), 2),
        "ending_revolver_balance": weeks[-1]["revolver_balance"],
    }


def expected_pay_date(invoice: dict) -> date:
    """Deterministic expected collection date for an open invoice.

    Uses the customer's observed payment behavior (historical average days to
    pay from invoice date), not the stated terms. That gap is the point: the
    forecast reflects how customers actually pay.
    """
    inv_date = invoice["invoice_date"]
    if isinstance(inv_date, str):
        inv_date = date.fromisoformat(inv_date)
    return inv_date + timedelta(days=int(round(invoice["customer_days_to_pay"])))


# A billing week does not collect as one lump. Customers pay across a
# spread; model each week's collections as three tranches around the lag.
COLLECTION_TRANCHES = [(0.25, -7.0), (0.50, 0.0), (0.25, 7.0)]


def split_sales_row(row: dict) -> list[tuple[float, float]]:
    """Split a forecast billing week into (amount, collection_lag_days) parts.

    Vantage Aerospace's share of new billings collects at Vantage's observed
    pay behavior, not the blended lag. Its stretch therefore pushes part of
    the late-quarter billings past the covenant test week, which is exactly
    the exposure the accelerate-Vantage scenario removes.
    """
    billings = float(row["billings"])
    vantage_share = float(row.get("vantage_share", 0.0))
    vantage_amt = billings * vantage_share
    parts = []
    for weight, offset in COLLECTION_TRANCHES:
        parts.append(((billings - vantage_amt) * weight, float(row["base_lag_days"]) + offset, "base"))
        if vantage_amt > 0:
            parts.append((vantage_amt * weight, float(row["vantage_lag_days"]) + offset, "vantage"))
    return parts


def build_weekly_flows(
    invoices: list[dict],
    bills: list[dict],
    fixed_items: list[dict],
    sales_forecast: list[dict],
    week1_monday: date,
    num_weeks: int = 13,
) -> tuple[list[float], list[float]]:
    """Assemble the deterministic weekly receipt and disbursement vectors.

    Receipts: open invoices at their expected pay dates, plus collections on
    forecast new billings (billing week start + the blended collection lag).
    Disbursements: open AP at due dates, plus every dated fixed-schedule item.
    """
    ar_items = [
        {"date": expected_pay_date(inv), "amount": inv["amount"]} for inv in invoices
    ]
    receipts = bucket_flows(ar_items, week1_monday, num_weeks)

    for row in sales_forecast:
        for amount, lag_days, _source in split_sales_row(row):
            billing_date = row["week_start"]
            if isinstance(billing_date, str):
                billing_date = date.fromisoformat(billing_date)
            collect_date = billing_date + timedelta(days=int(lag_days))
            w = date_to_week(collect_date, week1_monday, num_weeks)
            if w <= num_weeks:
                receipts[w - 1] += amount

    ap_items = [{"date": b["due_date"], "amount": b["amount"]} for b in bills]
    disbursements = bucket_flows(ap_items, week1_monday, num_weeks)

    fixed = bucket_flows(fixed_items, week1_monday, num_weeks)
    disbursements = [d + f for d, f in zip(disbursements, fixed)]

    return receipts, disbursements
