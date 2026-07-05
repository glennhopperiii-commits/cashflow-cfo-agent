# Cascade Precision Products, Inc. — Synthetic Data Design

Reference for the data in this folder. **The dataset is frozen**: a fixed seed
(7) and a fixed as-of anchor (Friday close 2026-08-21; week 1 begins Monday
2026-08-24, so the Aug 26 demo airs inside week 1). `cashflow_harness/data_gen.py`
produces every file, reconciles to the control totals below exactly, and is
byte-identical on every run — regeneration is a safety net, not a run-time step.
The Colab notebook embeds these files directly rather than generating them.

```
python -m cashflow_harness.data_gen   # reproduces this folder byte-for-byte
```

## Company Profile

- **Name:** Cascade Precision Products, Inc.
- **Business:** Contract manufacturer of precision-machined components for
  aerospace, defense, and industrial OEMs
- **Size:** ~$72M trailing revenue, ~240 employees
- **Ownership:** Acquired ten weeks ago by Granite Peak Partners (LBO).
  Lender group agented by Ridgeline Capital Bank.
- **Horizon:** 13 weeks, weekly buckets, starting the Monday after the latest
  Friday close

## Capital Structure and Thresholds

| Item | Value |
|---|---|
| Beginning cash (week 1 open) | $2,400,000 |
| Revolver limit | $15,000,000 |
| Revolver drawn at start | $6,000,000 ($9.0M availability) |
| Term loan | $38,000,000 |
| Debt service, end of week 13 | $2,200,000 ($1.25M amortization + $0.95M interest) |
| Operating cash floor | $1,500,000 (auto-draw in $250K increments to restore) |
| Sweep policy | Excess above floor + $500K buffer pays the revolver down |
| Liquidity covenant | Cash + undrawn availability >= $4,000,000, tested week 13 |

## Baked-In Stories (five)

1. **Top-customer term stretch (the trough driver).** Vantage Aerospace is
   ~22% of open AR ($4.2M exactly). Terms Net 45, observed behavior ~64 days.
   The $2.1M LR-7 milestone invoice is due in week 4 but lands in week 7 on
   observed behavior. Week 4 shows the hole; week 7 shows the landing.
2. **Growth working-capital build.** The aerospace ramp drives heavier AP due
   dates in weeks 3-7, a payroll step-up from week 5 (second shift), and
   forecast material purchases building through the quarter, ahead of ramp
   billings that collect weeks 9-13 and beyond.
3. **Lumpy scheduled outflows.** Week 5 insurance $450K, week 6 capex deposit
   $800K (discretionary), week 9 earn-out $1.0M, week 10 estimated tax $300K,
   week 13 debt service $2.2M.
4. **The covenant is tight but passes deterministically.** Cash troughs at
   ~$1.56M in week 8 after a $250K week-7 revolver draw (draws begin week 5).
   Week-13 liquidity lands at ~$4.63M, clearing the $4.0M covenant with ~$0.63M
   of headroom.
5. **The probabilistic view changes the decision.** Monte Carlo over
   collection timing and sales volume keeps the P50 above the covenant, but
   P(breach at week 13) is ~20% (18-22% band, seed 42). The single-point
   forecast looks fine; the distribution says the risk is material.

## Control Totals (verified by generation asserts and the testing checklist)

- Open AR = **$19,300,000** across ~122 invoices; top 5 customers ≈ 60%;
  Vantage Aerospace = **$4,200,000 (21.8%)**, days-to-pay 64, sigma 10
- Open AP = **$8,700,000** across 90 bills, due weeks 1-8, heaviest weeks 3-7
- Trailing 4 weeks: actual collections **6.0% under** the prior forecast,
  concentrated in one slipped Vantage invoice (~$0.4M in week -2)
- Deterministic path (seed 7): trough **$1,562,800 in week 8**; week-13
  liquidity **$4,631,300** (headroom **$631,300**); revolver draws
  $1.0M (wk 5), $1.0M (wk 6), $250K (wk 7), $1.5M (wk 9), $2.25M (wk 13);
  peak revolver $12.0M of the $15.0M limit
- Monte Carlo (1,000 iterations, seed 42): **P(breach) = 0.202**,
  P(floor unrestorable) = 0.0, week-13 liquidity P10 ≈ $3.62M / P50 ≈ $4.66M

## Modeling Notes

- **Collection timing.** Each open invoice carries its customer's historical
  days-to-pay and sigma. The deterministic engine collects at invoice date +
  days-to-pay (behavior, not stated terms). Monte Carlo samples a systematic
  per-customer shift (60% of sigma) plus per-invoice noise (80% of sigma).
- **New billings.** `sales_forecast.csv` ramps weekly billings from $1.38M to
  $2.24M with sigma rising 10% -> 15% (ramp uncertainty). Collections split
  into three tranches (25/50/25 at lag -7/0/+7 days) around a 61-day blended
  lag; Vantage's 22% share collects at Vantage's 64-day behavior instead.
  Late-quarter Vantage billings therefore collect past week 13, which is the
  dollars the accelerate-Vantage scenario pulls back into the quarter.
- **Aged/disputed AR tail.** Two small accounts (Ridgefield Turbine,
  Sturgeon Bay Marine; $835K combined) pay at 112-115 days, past the horizon.
- **"Below floor" probability** means ending cash below the $1.5M floor even
  after revolver draws, i.e. the draw needed exceeded remaining availability.
  Zero in the base case: the floor is always defendable inside the $15M limit.

## Data Files

1. `company_context.md` — narrative context: the LBO, covenant terms, the
   Vantage stretch, the ramp, every scheduled one-timer
2. `ar_open_invoices.json` — 122 open invoices with customer behavior stats
3. `ap_open_bills.json` — 90 open bills with category and discretionary flag
4. `fixed_schedule.csv` — payroll (biweekly), rent, benefits, utilities,
   one-timers, debt service, forecast ramp material purchases
5. `sales_forecast.csv` — weekly billings, sigma, lags, Vantage share
6. `historical_actuals.csv` — trailing 4 weeks, forecast vs. actual with the
   Vantage split for the variance bridge
7. `facility_terms.json` — cash, revolver, floor, covenant, debt service
