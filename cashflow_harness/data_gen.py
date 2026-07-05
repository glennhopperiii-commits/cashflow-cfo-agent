"""Synthetic data generator for Cascade Precision Products, Inc.

Generates every file in data/ so the control totals in data/DATA_DESIGN.md
reconcile exactly:

  - Open AR = $19,300,000 across ~120 invoices, Vantage Aerospace = $4,200,000
  - Open AP = $8,700,000 across ~90 bills
  - Fixed schedule with every one-time item in its specified week
  - Trailing 4-week actuals with collections ~6% under the prior forecast,
    driven by the Vantage slippage

The CALIBRATION section holds the knobs that shape the weekly cash path.
They are tuned so the deterministic forecast troughs near $1.6M in week 8
and clears the week-13 covenant with roughly $0.6M of headroom, and the
Monte Carlo breach probability lands in the 18-22% band.

Run: python -m cashflow_harness.data_gen
"""

import csv
import json
from datetime import date, timedelta

import numpy as np

from .config import (
    BEGINNING_CASH,
    DATA_ASOF,
    COVENANT_TEST_WEEK,
    COVENANT_THRESHOLD,
    DATA_DIR,
    DEBT_SERVICE_AMORT,
    DEBT_SERVICE_INTEREST,
    DRAW_INCREMENT,
    GEN_SEED,
    NUM_WEEKS,
    OPERATING_FLOOR,
    REVOLVER_DRAWN,
    REVOLVER_LIMIT,
    SWEEP_BUFFER,
    TERM_LOAN_BALANCE,
)

# ---------------------------------------------------------------------------
# CALIBRATION
# ---------------------------------------------------------------------------

AR_TOTAL = 19_300_000
AP_TOTAL = 8_700_000

# Target weekly profile for open-AR collections (weeks 1..13, then tail past
# the horizon). Week 4 has the hole where the $2.1M Vantage collection was
# penciled; week 7 has it landing per Vantage's observed 64-day behavior.
AR_WEEK_PROFILE = {
    1: 1_820_000,
    2: 1_435_000,
    3: 2_345_000,
    4: 1_770_000,   # the Vantage hole: the $2.1M penciled here is absent
    5: 2_435_000,
    6: 2_020_000,
    7: 2_600_000,   # includes the $2.1M Vantage invoice landing late
    8: 1_890_000,
    9: 1_100_000,
    10: 450_000,
    11: 450_000,
    12: 50_000,
    13: 100_000,
    14: 835_000,    # tail: collects beyond the horizon
}

# Open-AP due-date profile (weeks 1..8). Heavier in weeks 3-7: material buys
# for the aerospace ramp were ordered in the trailing month on Net 30/45.
AP_WEEK_PROFILE = {
    1: 850_000,
    2: 950_000,
    3: 1_150_000,
    4: 1_200_000,
    5: 1_250_000,
    6: 1_200_000,
    7: 1_150_000,
    8: 950_000,
}

# Biweekly payroll: base, then with the added second shift from week 5.
PAYROLL_BASE = 745_000
PAYROLL_RAMPED = 815_000
PAYROLL_WEEKS = [1, 3, 5, 7, 9, 11, 13]
PAYROLL_RAMP_FROM_WEEK = 5

RENT_MONTHLY = 95_000
RENT_WEEKS = [2, 6, 10]
BENEFITS_MONTHLY = 205_000
BENEFITS_WEEKS = [1, 5, 9]
UTILITIES_WEEKLY = 70_000

# Forecast material purchases for the ramp (paid Net 30 on new POs, so they
# start hitting cash in week 4 and build through the quarter). This is the
# growth working-capital story: inventory goes out the door as cash before
# the ramp shipments bill and collect.
MATERIALS_FORECAST = {
    1: 350_000,
    2: 420_000,
    3: 500_000,
    4: 600_000,
    5: 700_000,
    6: 780_000,
    7: 860_000,
    8: 1_290_000,
    9: 1_350_000,
    10: 1_100_000,
    11: 1_300_000,
    12: 1_420_000,
    13: 770_000,
}

# One-time scheduled outflows: (week, item, category, amount, discretionary)
ONE_TIMERS = [
    (5, "Semiannual property & casualty insurance premium", "insurance", 450_000, False),
    (6, "Capex deposit: Hermle C42 5-axis machining center", "capex", 800_000, True),
    (9, "Seller note earn-out payment (Granite Peak acquisition)", "acquisition", 1_000_000, False),
    (10, "Estimated federal income tax payment", "tax", 300_000, False),
]

# Forecast new billings by week: ramping as the aerospace program ships.
SALES_BILLINGS = [
    1_380_000, 1_420_000, 1_460_000, 1_520_000, 1_580_000, 1_660_000,
    1_760_000, 1_880_000, 1_990_000, 2_080_000, 2_150_000, 2_200_000,
    2_240_000,
]
SALES_SIGMA_PCT = [0.10, 0.10, 0.11, 0.11, 0.12, 0.12, 0.13, 0.13, 0.14, 0.14, 0.15, 0.15, 0.15]
SALES_BASE_LAG_DAYS = 61       # blended non-Vantage collection behavior
SALES_VANTAGE_SHARE = 0.22
SALES_VANTAGE_LAG_DAYS = 64    # Vantage's observed days-to-pay

# Trailing 4 weeks: prior forecast vs. actual collections. The week -2 miss
# is the Vantage invoice that slipped; total actuals land ~6% under forecast.
HISTORY = [
    # (forecast_total, forecast_vantage, actual_total, actual_vantage, actual_disb)
    (1_950_000, 310_000, 1_905_000, 305_000, 1_985_000),
    (1_880_000, 420_000, 1_452_000, 20_000, 1_860_000),
    (1_760_000, 180_000, 1_741_000, 175_000, 2_015_000),
    (1_850_000, 240_000, 1_896_000, 262_000, 1_910_000),
]

# ---------------------------------------------------------------------------
# Customers and vendors
# ---------------------------------------------------------------------------

# (name, segment, terms_days, days_to_pay, pay_sigma, ar_total)
# Top 5 = $11.58M = 60% of AR. Vantage = $4.2M = 21.8%.
CUSTOMERS = [
    ("Vantage Aerospace", "aerospace", 45, 64, 10.0, 4_200_000),
    ("Trident Defense Systems", "defense", 45, 51, 6.0, 2_400_000),
    ("Pacific Turbine Group", "aerospace", 60, 66, 7.0, 2_000_000),
    ("Halvorsen Industrial", "industrial", 30, 38, 5.0, 1_650_000),
    ("Bellingham Aerostructures", "aerospace", 45, 50, 6.0, 1_330_000),
    ("Redline Motion Systems", "industrial", 30, 36, 4.0, 980_000),
    ("Cobalt Marine Propulsion", "defense", 60, 65, 8.0, 920_000),
    ("Ironwood Energy Equipment", "industrial", 45, 52, 7.0, 860_000),
    ("Northgate Avionics", "aerospace", 45, 49, 5.0, 810_000),
    ("Keystone Hydraulics", "industrial", 30, 37, 5.0, 740_000),
    ("Blue Ridge Turbomachinery", "aerospace", 60, 67, 8.0, 690_000),
    ("Falcon Gear Works", "industrial", 30, 39, 5.0, 470_000),
    ("Saginaw Rail Components", "industrial", 60, 78, 11.0, 405_000),
    ("Tectonic Mining Systems", "industrial", 45, 55, 8.0, 330_000),
    ("Orchard Robotics", "industrial", 30, 41, 6.0, 250_000),
    ("Whitewater Compressor", "industrial", 45, 54, 7.0, 180_000),
    ("Camas Instrument Works", "aerospace", 30, 40, 6.0, 150_000),
    ("Deschutes Fabrication", "industrial", 30, 42, 7.0, 100_000),
    # Aged / disputed accounts: pay behavior runs past the horizon, so most
    # of this AR collects beyond week 13 (the tail).
    ("Ridgefield Turbine Services", "industrial", 60, 115, 12.0, 515_000),
    ("Sturgeon Bay Marine Systems", "industrial", 60, 112, 10.0, 320_000),
]

VENDORS = [
    ("Olympic Alloys", "raw material"),
    ("Selkirk Specialty Steel", "raw material"),
    ("Cascadia Titanium Supply", "raw material"),
    ("Rainier Tool & Carbide", "tooling"),
    ("Columbia Heat Treat", "outside processing"),
    ("Willamette Plating & Anodize", "outside processing"),
    ("Kootenai Coatings", "outside processing"),
    ("Puget Freight Lines", "freight"),
    ("Evergreen Industrial Gases", "consumables"),
    ("Tacoma Abrasives", "consumables"),
    ("Harbor Packaging", "consumables"),
    ("Skagit Machine Rebuild", "maintenance"),
    ("Baker Calibration Services", "maintenance"),
    ("CNC Spares Direct", "maintenance"),
    ("Sound Fastener Supply", "raw material"),
]

# Explicit discretionary AP bills: (vendor, category, week, amount, memo)
DISCRETIONARY_BILLS = [
    ("Rainier Tool & Carbide", "tooling", 6, 120_000, "Tooling package upgrade, deferrable per ops"),
    ("Skagit Machine Rebuild", "maintenance", 7, 85_000, "Spindle rebuild on backup mill, non-critical"),
    ("Harbor Packaging", "consumables", 5, 45_000, "Packaging inventory top-up, above reorder point"),
    ("CNC Spares Direct", "maintenance", 8, 60_000, "Spare parts stocking order, deferrable"),
]

VANTAGE_INVOICES = [
    # (amount, age_days, memo)  age = days before the Friday close
    (2_100_000, 19, "Milestone billing, LR-7 landing gear program"),
    (620_000, 55, "Production release 4180, actuator housings"),
    (560_000, 40, "Production release 4197, actuator housings"),
    (480_000, 30, "Tooling amortization billing, LR-7"),
    (440_000, 10, "Production release 4211, wing rib fittings"),
]


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def latest_friday_close(today: date | None = None) -> date:
    # Default to the frozen demo anchor so generation is fully deterministic:
    # same seed + same anchor = byte-identical files every time.
    today = today or date.fromisoformat(DATA_ASOF)
    # Most recent Friday on or before the anchor
    return today - timedelta(days=(today.weekday() - 4) % 7)


def _spread(rng: np.random.Generator, total: int, n: int, low_frac=0.4, high_frac=2.2) -> list[int]:
    """Split total into n positive amounts that sum exactly to total."""
    weights = rng.uniform(low_frac, high_frac, n)
    raw = weights / weights.sum() * total
    amounts = [int(round(a, -2)) for a in raw]
    amounts[-1] += total - sum(amounts)
    return amounts


def _weekday_date(week1_monday: date, week: int, rng: np.random.Generator) -> date:
    """A business-day date inside the given week (1-indexed)."""
    return week1_monday + timedelta(days=(week - 1) * 7 + int(rng.integers(0, 5)))


def generate_ar(rng: np.random.Generator, close: date, week1_monday: date) -> list[dict]:
    invoices = []
    seq = 5001

    def add(customer, amount, invoice_date, memo=""):
        nonlocal seq
        name, segment, terms, dtp, sigma, _ = customer
        invoices.append({
            "invoice_id": f"INV-{seq}",
            "customer": name,
            "segment": segment,
            "invoice_date": invoice_date.isoformat(),
            "due_date": (invoice_date + timedelta(days=terms)).isoformat(),
            "terms": f"Net {terms}",
            "amount": int(amount),
            "customer_days_to_pay": dtp,
            "customer_pay_sigma": sigma,
            "memo": memo,
        })
        seq += 1

    vantage = CUSTOMERS[0]
    for amount, age, memo in VANTAGE_INVOICES:
        add(vantage, amount, close - timedelta(days=age), memo)

    # Remaining customers: assign each invoice a target collection week from
    # the AR profile (less what Vantage already covers), then back out the
    # invoice date from the customer's observed days-to-pay.
    profile = dict(AR_WEEK_PROFILE)
    for inv in invoices:  # subtract Vantage from its landing weeks
        pay = date.fromisoformat(inv["invoice_date"]) + timedelta(days=int(inv["customer_days_to_pay"]))
        w = min((pay - week1_monday).days // 7 + 1, 14)
        w = max(w, 1)
        profile[w] = profile.get(w, 0) - inv["amount"]

    # Slowest payers sample first so they claim the late weeks only they can
    # reach; fast payers then fill what remains of the early weeks.
    weeks = sorted(profile)
    for customer in sorted(CUSTOMERS[1:], key=lambda c: -c[3]):
        name, segment, terms, dtp, sigma, total = customer
        n_inv = max(3, int(round(total / 140_000)))
        amounts = _spread(rng, total, n_inv)
        # Feasible landing weeks: invoice must predate the close, so the pay
        # offset from week 1 cannot exceed days_to_pay - 3.
        max_week = min(14, (dtp - 3) // 7 + 1)
        feasible = [w for w in weeks if w <= max_week]
        for amt in amounts:
            # Fill the latest feasible week that still has unmet profile.
            # Slowest payers run first, so the late weeks only they can
            # reach get claimed before they fall back to early weeks.
            # Only weeks with room for most of this invoice, so a small
            # residual bucket doesn't swallow a big invoice and starve the
            # early weeks.
            open_weeks = [x for x in feasible if profile[x] >= amt * 0.5]
            w = max(open_weeks) if open_weeks else max(feasible, key=lambda x: profile[x])
            # Pay date lands on a business day inside week w (week 14 = tail)
            jitter_max = min(5, dtp - 3 - (w - 1) * 7)
            pay_offset = (w - 1) * 7 + int(rng.integers(0, max(jitter_max, 1)))
            invoice_date = week1_monday + timedelta(days=pay_offset - dtp)
            if invoice_date > close:
                invoice_date = close - timedelta(days=int(rng.integers(1, 5)))
            add(customer, amt, invoice_date)
            landed = min((invoice_date + timedelta(days=dtp) - week1_monday).days // 7 + 1, 14)
            profile[landed] = profile.get(landed, 0) - amt

    assert sum(i["amount"] for i in invoices) == AR_TOTAL
    return invoices


def generate_ap(rng: np.random.Generator, close: date, week1_monday: date) -> list[dict]:
    bills = []
    seq = 9001

    def add(vendor, category, due, amount, discretionary, memo=""):
        nonlocal seq
        bills.append({
            "bill_id": f"AP-{seq}",
            "vendor": vendor,
            "category": category,
            "due_date": due.isoformat(),
            "amount": int(amount),
            "discretionary": discretionary,
            "memo": memo,
        })
        seq += 1

    for vendor, category, week, amount, memo in DISCRETIONARY_BILLS:
        add(vendor, category, _weekday_date(week1_monday, week, rng), amount, True, memo)

    disc_total = sum(b["amount"] for b in bills)
    remaining = AP_TOTAL - disc_total

    profile = dict(AP_WEEK_PROFILE)
    for vendor, category, week, amount, _ in DISCRETIONARY_BILLS:
        profile[week] -= amount

    n_bills = 86
    weeks = sorted(profile)
    week_weights = np.array([max(profile[w], 1.0) for w in weeks], dtype=float)
    amounts = _spread(rng, remaining, n_bills, 0.3, 2.5)
    for amt in amounts:
        w = int(rng.choice(weeks, p=week_weights / week_weights.sum()))
        vendor, category = VENDORS[int(rng.integers(0, len(VENDORS)))]
        # Ramp buys concentrate in raw material / outside processing weeks 3-7
        memo = "Aerospace ramp material buy" if (3 <= w <= 7 and category in ("raw material", "outside processing") and amt > 90_000) else ""
        add(vendor, category, _weekday_date(week1_monday, w, rng), amt, False, memo)
        profile[w] -= amt
        week_weights = np.array([max(profile[w], 1.0) for w in weeks], dtype=float)

    assert sum(b["amount"] for b in bills) == AP_TOTAL
    return bills


def generate_fixed_schedule(week1_monday: date) -> list[dict]:
    rows = []

    def add(week, day_offset, item, category, amount, discretionary):
        rows.append({
            "week": week,
            "date": (week1_monday + timedelta(days=(week - 1) * 7 + day_offset)).isoformat(),
            "item": item,
            "category": category,
            "amount": int(amount),
            "discretionary": discretionary,
        })

    for w in PAYROLL_WEEKS:
        amount = PAYROLL_RAMPED if w >= PAYROLL_RAMP_FROM_WEEK else PAYROLL_BASE
        label = "Biweekly payroll" + (" (incl. second shift, aerospace ramp)" if w >= PAYROLL_RAMP_FROM_WEEK else "")
        add(w, 4, label, "payroll", amount, False)

    for w in RENT_WEEKS:
        add(w, 0, "Facility rent, monthly", "occupancy", RENT_MONTHLY, False)

    for w in BENEFITS_WEEKS:
        add(w, 2, "Health benefits premium, monthly", "benefits", BENEFITS_MONTHLY, False)

    for w in range(1, NUM_WEEKS + 1):
        add(w, 3, "Utilities & plant services", "operations", UTILITIES_WEEKLY, False)

    for week, item, category, amount, discretionary in ONE_TIMERS:
        add(week, 2, item, category, amount, discretionary)

    add(13, 4, "Term loan quarterly amortization", "debt service", DEBT_SERVICE_AMORT, False)
    add(13, 4, "Term loan quarterly interest", "debt service", DEBT_SERVICE_INTEREST, False)

    for w in sorted(MATERIALS_FORECAST):
        add(w, 1, "Material purchases, forecast (aerospace ramp POs, Net 30)",
            "materials forecast", MATERIALS_FORECAST[w], False)

    return sorted(rows, key=lambda r: (r["week"], r["date"]))


def generate_sales_forecast(week1_monday: date) -> list[dict]:
    rows = []
    for i, billings in enumerate(SALES_BILLINGS):
        rows.append({
            "week": i + 1,
            "week_start": (week1_monday + timedelta(weeks=i)).isoformat(),
            "billings": int(billings),
            "sigma": int(round(billings * SALES_SIGMA_PCT[i], -3)),
            "base_lag_days": SALES_BASE_LAG_DAYS,
            "vantage_share": SALES_VANTAGE_SHARE,
            "vantage_lag_days": SALES_VANTAGE_LAG_DAYS,
        })
    return rows


def generate_historical(close: date) -> list[dict]:
    rows = []
    net_flows = [(f[2] - f[4]) for f in HISTORY]
    start_cash = BEGINNING_CASH - sum(net_flows)
    cash = start_cash
    for i, (fc, fc_v, ac, ac_v, disb) in enumerate(HISTORY):
        week_ending = close - timedelta(weeks=len(HISTORY) - 1 - i)
        cash += ac - disb
        rows.append({
            "week_ending": week_ending.isoformat(),
            "forecast_collections": fc,
            "forecast_vantage": fc_v,
            "actual_collections": ac,
            "actual_vantage": ac_v,
            "actual_disbursements": disb,
            "actual_ending_cash": int(cash),
        })
    assert rows[-1]["actual_ending_cash"] == BEGINNING_CASH
    return rows


def generate_facility_terms(close: date, week1_monday: date) -> dict:
    return {
        "company": "Cascade Precision Products, Inc.",
        "as_of_close": close.isoformat(),
        "week1_monday": week1_monday.isoformat(),
        "num_weeks": NUM_WEEKS,
        "beginning_cash": BEGINNING_CASH,
        "revolver_limit": REVOLVER_LIMIT,
        "revolver_drawn": REVOLVER_DRAWN,
        "revolver_availability": REVOLVER_LIMIT - REVOLVER_DRAWN,
        "operating_cash_floor": OPERATING_FLOOR,
        "sweep_buffer": SWEEP_BUFFER,
        "draw_increment": DRAW_INCREMENT,
        "covenant": {
            "type": "minimum liquidity (cash + undrawn revolver availability)",
            "threshold": COVENANT_THRESHOLD,
            "test_week": COVENANT_TEST_WEEK,
            "consequence": "event of default",
            "certified_to": "Ridgeline Capital Bank, agent for the lender group",
        },
        "term_loan": {
            "balance": TERM_LOAN_BALANCE,
            "quarterly_amortization": DEBT_SERVICE_AMORT,
            "quarterly_interest": DEBT_SERVICE_INTEREST,
            "debt_service_due_week": 13,
        },
    }


def generate_context(close: date, week1_monday: date) -> str:
    return f"""# Cascade Precision Products, Inc. -- Treasury Context

As of the Friday close on {close.isoformat()}. Forecast horizon: 13 weeks
beginning Monday {week1_monday.isoformat()}.

## Ownership and the ask

Granite Peak Partners closed its leveraged buyout of Cascade Precision ten
weeks ago. The capital structure is a $38.0M term loan and a $15.0M revolver
($6.0M drawn at the close date), both agented by Ridgeline Capital Bank. The
sponsor's first standing request is a weekly 13-week cash flow forecast with
covenant visibility. This is the first one under new ownership.

## The covenant

Minimum liquidity (cash plus undrawn revolver availability) of $4.0M, measured
weekly, hard-tested and certified to the lender at the week 13 quarter-end. A
breach is an event of default under the credit agreement. Quarterly term-loan
debt service of $2.2M ($1.25M amortization, $0.95M interest) is due at the end
of week 13.

Treasury policy: operating cash floor of $1.5M. If ending cash would fall
below the floor, draw the revolver (in $250K increments) to restore it. When
cash runs comfortably above the floor, sweep the excess against the revolver,
leaving a $500K buffer.

## Customer concentration and the Vantage term stretch

Vantage Aerospace is the largest account at roughly 22% of open AR ($4.2M).
Vantage is on Net 45 terms but its payment behavior has stretched to roughly
64 days over the last two quarters as its own program payments slowed. The
practical effect: a $2.1M milestone collection on the LR-7 landing gear
program that the prior forecast penciled for week 4 (its contractual due
date) is now expected to land in week 7 or 8. Vantage remains a sound credit;
this is timing, not collectability. Procurement at Vantage has been
non-committal about acceleration but has paid to a negotiated date before
when offered a modest early-pay incentive.

The top five customers (Vantage Aerospace, Trident Defense Systems, Pacific
Turbine Group, Halvorsen Industrial, Bellingham Aerostructures) are about 60%
of open AR.

## The aerospace ramp

Cascade won a multi-year aerospace program earlier this year. Shipments ramp
through the quarter: material buys and outside processing are already flowing
(heavier AP due weeks 3 through 7), a second shift was added (payroll steps
up from the week 5 cycle), and the associated billings build from week 6
onward, collecting on normal lags in weeks 9 through 13 and beyond. Cash goes
out before it comes in. This is deliberate growth working capital, not
deterioration.

## Scheduled one-time outflows

- Week 5: semiannual property & casualty insurance premium, $450K
- Week 6: capex deposit on a Hermle C42 5-axis machining center, $800K
  (progress deposit; the builder has flexibility on the deposit date within
  the quarter, and slots the machine for delivery next quarter)
- Week 9: seller note earn-out payment from the acquisition, $1.0M (fixed
  date per the purchase agreement)
- Week 10: estimated federal income tax payment, $300K
- Week 13: term loan quarterly debt service, $2.2M

## Trailing performance

Over the trailing 4 weeks, collections came in about 6% under the prior
forecast. The miss is concentrated in one week and one customer: a Vantage
invoice of roughly $0.4M slipped past its forecast date. Disbursements ran
close to plan. This is the same behavior now baked into the week 4 to week 7
slip on the $2.1M milestone.

## Notes for the forecast

- The borrowing base comfortably exceeds the revolver commitment through the
  horizon; availability is constrained by the $15.0M limit, not the base.
- Payroll is biweekly (weeks 1, 3, 5, 7, 9, 11, 13), stepping up when the
  second shift loads in.
- The capex deposit and a small set of AP items are flagged discretionary;
  everything else is committed.
"""


def generate_all(out_dir=None, today: date | None = None, seed: int = GEN_SEED) -> dict:
    """Generate every data file. Returns a reconciliation summary."""
    out = out_dir or DATA_DIR
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    close = latest_friday_close(today)
    week1_monday = close + timedelta(days=3)

    invoices = generate_ar(rng, close, week1_monday)
    bills = generate_ap(rng, close, week1_monday)
    fixed = generate_fixed_schedule(week1_monday)
    sales = generate_sales_forecast(week1_monday)
    history = generate_historical(close)
    facility = generate_facility_terms(close, week1_monday)

    def write_json_lines(path, records):
        # One record per line: diffable, and compact enough to embed the
        # frozen dataset directly in the notebook.
        with open(path, "w") as f:
            f.write("[\n" + ",\n".join(json.dumps(r) for r in records) + "\n]\n")

    write_json_lines(out / "ar_open_invoices.json", invoices)
    write_json_lines(out / "ap_open_bills.json", bills)
    with open(out / "facility_terms.json", "w") as f:
        json.dump(facility, f, indent=2)

    with open(out / "fixed_schedule.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["week", "date", "item", "category", "amount", "discretionary"])
        writer.writeheader()
        writer.writerows(fixed)

    with open(out / "sales_forecast.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(sales[0].keys()))
        writer.writeheader()
        writer.writerows(sales)

    with open(out / "historical_actuals.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(history[0].keys()))
        writer.writeheader()
        writer.writerows(history)

    with open(out / "company_context.md", "w") as f:
        f.write(generate_context(close, week1_monday))

    vantage_total = sum(i["amount"] for i in invoices if i["customer"] == "Vantage Aerospace")
    hist_fc = sum(h["forecast_collections"] for h in history)
    hist_ac = sum(h["actual_collections"] for h in history)
    return {
        "close": close.isoformat(),
        "week1_monday": week1_monday.isoformat(),
        "ar_total": sum(i["amount"] for i in invoices),
        "ar_invoice_count": len(invoices),
        "vantage_total": vantage_total,
        "vantage_pct": round(vantage_total / AR_TOTAL, 4),
        "ap_total": sum(b["amount"] for b in bills),
        "ap_bill_count": len(bills),
        "fixed_total": sum(r["amount"] for r in fixed),
        "history_miss_pct": round(1 - hist_ac / hist_fc, 4),
    }


if __name__ == "__main__":
    summary = generate_all()
    print("Generated data/ for Cascade Precision Products")
    for k, v in summary.items():
        print(f"  {k}: {v:,}" if isinstance(v, int) else f"  {k}: {v}")
