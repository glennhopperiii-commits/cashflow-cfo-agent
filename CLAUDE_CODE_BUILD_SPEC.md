# Cascade Precision 13-Week Cash Flow Agent — Build Spec

**Status: Phase 1 AND Phase 2 complete and verified.** Phase 1: 20/20 checklist items
pass. Phase 2: pipeline runs end to end in the UI with numbers matching the notebook
exactly; the deterministic↔probabilistic toggle, the blocking review gate (edits land in
the final output), replay mode, and the workbook download are all verified in-browser.
Start everything with `Start Demo.command` (or `uvicorn backend.server:app --port 8000`
+ `npm run dev` in frontend/).

The AFP FP&A Virtual Summit demo (Ramp-sponsored, airs Aug 26, pre-recorded). One idea:
an agent harness lets finance keep deterministic control while gaining probabilistic
reasoning. The deterministic-to-probabilistic toggle is the star.

## What exists

```
cashflow-cfo-agent/
├── CLAUDE_CODE_BUILD_SPEC.md      # this file
├── requirements.txt
├── .env                           # ANTHROPIC_API_KEY (never committed / hardcoded)
├── .env.example
├── cashflow_harness/              # Phase 1 package — pure, importable functions
│   ├── config.py                  # model, thresholds, MC settings, system + initial prompts
│   ├── data_gen.py                # synthetic data generator (calibrated, seeded)
│   ├── engine.py                  # deterministic roll-forward + revolver mechanics (pure)
│   ├── montecarlo.py              # probabilistic layer (numpy, seeded)
│   ├── tools.py                   # the 10 agent tools (Phase 2 imports these unchanged)
│   ├── tool_schemas.py            # Anthropic tool definitions
│   ├── agent.py                   # tool-use loop, review gate as a callback
│   ├── report.py                  # 13-week TWCF workbook: Excel always, Google Sheet in Colab
│   └── logger.py                  # audit trail + replay capture
├── notebook/CashFlow_Agent.ipynb  # Phase 1 deliverable — runs end to end in Colab
├── data/                          # generated; DATA_DESIGN.md documents design + control totals
└── output/                        # audit_log.json, replay_capture.json, final_report.json,
                                   # cashflow_13wk.xlsx (the sponsor deliverable)
```

Model: `claude-sonnet-5` in `config.py`; the harness is model-agnostic — swap the string.

## The verified numbers

**The dataset is frozen**: seed 7 plus a fixed anchor (Friday close 2026-08-21, week 1 =
Monday 2026-08-24, chosen so the Aug 26 airing falls inside week 1). Regenerating with
`python -m cashflow_harness.data_gen` reproduces `data/` byte-for-byte; the Colab
notebook embeds the frozen files directly (section 1.4) and verifies every control
total in Part 2.1 before running anything.

| Metric | Value |
|---|---|
| Open AR / Vantage share | $19,300,000 / $4,200,000 (21.8%), 122 invoices, top-5 = 60% |
| Open AP | $8,700,000, 90 bills, heaviest weeks 3-7 |
| Deterministic trough | **$1,562,800 in week 8**, after a $250K week-7 draw (draws start wk 5) |
| Week-13 covenant liquidity | **$4,631,300** vs $4.0M threshold → **$631,300 headroom** |
| Revolver path | $6.0M → $12.0M peak (limit $15.0M); draws wk 5, 6, 7, 9, 13 |
| P(covenant breach wk 13) | **20.2%** (1,000 iterations, seed 42; ~19% across seeds) |
| P(floor unrestorable) | 0.0% — the floor is always defendable inside the limit |
| Trailing 4-week variance | Collections 6.0% under forecast, 87% attributable to Vantage timing |

Scenario levers (from the driver sweep, each vs. base):

| Scenario | Δ wk-13 headroom | P(breach) |
|---|---|---|
| Accelerate Vantage to Net 45 | +$1,103,300 | 20.2% → 1.3% |
| Defer capex deposit to wk 14 (past the test) | +$800,000 | → 3.1% |
| Defer capex deposit to wk 8 (inside the quarter) | $0 | unchanged |
| All customers +7 days | −$1,570,700 | → 91% |
| Sales −10% | −$703,130 | → 51% |

The zero on the two-week deferral is a feature, not a bug: covenant liquidity
(cash + availability) is invariant to revolver draws and sweeps, so only flows that
cross the week-13 boundary move deterministic headroom. The agent discovers and
narrates this correctly.

## Architecture decisions worth knowing

- **Engine purity.** `engine.run_forecast()` is a pure function; Monte Carlo re-runs it
  per iteration. Revolver mechanics: below the $1.5M floor auto-draw in $250K increments
  capped at availability; above floor + $500K buffer, sweep the revolver down.
- **Behavior-based timing.** The deterministic forecast collects each invoice at
  invoice date + the customer's observed days-to-pay (not stated terms). The gap between
  Vantage's Net 45 terms and its 64-day behavior is what moves the $2.1M milestone from
  the week-4 pencil to the week-7 landing.
- **Monte Carlo sampling.** Per iteration: a systematic per-customer pay-timing shift
  (60% of sigma) + per-invoice noise (80% of sigma); weekly billings ~ N(forecast, sigma);
  new-billing collections split into 25/50/25 tranches at blended-lag −7/0/+7 days with
  small systematic + per-week lag noise. Tranches keep boundary exposure smooth and the
  MC median centered on the deterministic path (within ~$50-90K).
- **Vantage share of new billings** (22%) collects at Vantage behavior, not the blended
  lag — that is the mass sitting past week 13 that the accelerate-Vantage scenario pulls
  back inside the quarter. This is what makes the recommended action genuinely move
  deterministic headroom, not just the breach odds.
- **"Below floor" probability** = ending cash below floor *after* draws (availability
  exhausted). With auto-draw, pre-revolver dips are routine; unrestorable dips are the
  treasury risk.
- **Review gate as a callback.** `run_agent(review_handler=...)`. Notebook passes an
  in-cell prompt loop; Phase 2 passes a WebSocket-blocking handler; None auto-approves
  (CLI). Verified: an edit made at the gate lands verbatim in `output/final_report.json`
  with `reviewer_action: "edited"`.
- **Event protocol kept verbatim from HFMA** so the Phase 2 frontend clones cleanly:
  `step_started`, `step_completed`, `agent_text`, `review_requested`,
  `pipeline_complete`, plus `report_generated` (HFMA precedent: its post-run PDF);
  frontend sends `review_submitted`. `DEMO_DELAYS` pacing exists in agent.py, scaled by
  `pace` (0 in notebook/CLI, 1.0 for the recorded demo).
- **The sponsor deliverable is a spreadsheet.** After the pipeline completes, agent.py
  calls `report.write_xlsx()` (never allowed to break the run): a traditional 13-week
  TWCF — receipts by customer (top 5 + other + forecast new billings), disbursements by
  category, cash-before-revolver mechanics, and the revolver/covenant block, with
  accounting formats and the covenant PASS/BREACH flag. `build_forecast_grid()` asserts
  every line ties to the engine's weekly totals to the dollar. `report.to_google_sheet()`
  publishes the same grid as a real Google Sheet — zero-setup in Colab
  (`google.colab.auth` + preinstalled gspread), or gspread + application-default
  credentials elsewhere. The notebook's section 11 covers both paths.

## The 10 tools

1. `load_facility_and_position` — cash, revolver, floor, covenant, debt service
2. `load_receivables` — customer subtotals, concentration, term-stretch flags, expected collections by week
3. `load_payables_and_fixed` — AP by due week + fixed schedule by category; one-timers; discretionary list
4. `build_deterministic_forecast` — 13-week table, trough, headroom
5. `run_monte_carlo` — P10/50/90 bands, trough distribution, two breach probabilities
6. `run_scenario` — `driver_sweep` (tornado) or single what-ifs: `slip_collections`,
   `accelerate_collection`, `defer_item`, `sales_change`, `stretch_ap`; returns deltas vs base
7. `compute_variance` — trailing 4-week bridge, timing-vs-volume attribution
8. `draft_cash_narrative` — pass-through: 4 sections with confidence + flags, plus the single recommended action
9. `submit_for_review` — the blocking human gate
10. `log_output` — final report + audit trail

## How to run

```bash
cd cashflow-cfo-agent
pip install -r requirements.txt          # .env needs ANTHROPIC_API_KEY
python -m cashflow_harness.data_gen      # regenerate data (seeded, reproducible)
python -m cashflow_harness.agent         # CLI mode, auto-approve gate
# or open notebook/CashFlow_Agent.ipynb  # full walkthrough with the interactive gate
```

## Phase 2 (complete) — the demo UI

Wraps, doesn't rewrite: `backend/server.py` imports `cashflow_harness.agent.run_agent`
and `cashflow_harness.tools` unchanged and supplies the WebSocket implementation of the
review-gate callback (an asyncio.Event the agent task parks on). Event protocol is the
HFMA protocol verbatim plus `report_generated`. `PACE = 1.0` applies the demo delays.

```
backend/                     # FastAPI: ws://localhost:8000/ws + REST
│                            # run/review/reset/replay/status/events/report (xlsx)
frontend/                    # React 19 + Vite + Tailwind 4 (HFMA design system)
├── src/hooks/useAgentSocket.js   # WS state machine; run_scenario accumulates;
│                                 # review payload carries recommended_action
├── src/lib/format.js             # accounting formats (parens, tabular numerals)
└── src/components/
    ├── Header / PipelineView / StepCard / StatusBadge / ActivityFeed / AuditLog / InfoPanel
    ├── ForecastDashboard         # composes the money shots + the D<->P toggle
    ├── FanChart                  # hand-rolled SVG: cash + liquidity, floor/covenant
    │                             # lines, event markers, P10-P90 fans, breach callout
    ├── RevolverPanel             # drawn vs availability vs $15M commitment
    ├── CovenantGauge             # wk-13 needle; P mode shows P10-P90 span + breach %
    ├── VarianceWaterfall         # forecast -> Vantage timing -> volume -> actual
    ├── DriverTornado             # sweep ranked by delta headroom, breach % labels
    └── ReviewGate / ReviewSection  # + RecommendedActionCard sign-off
```

Layout: 36% pipeline spine (10 step cards with per-step treasury summaries) · 64% main
panel (dashboard charts light up as the agent produces their data, activity feed below;
ReviewGate takes over at the gate). Charts are dependency-free SVG.

**Verified in-browser**: full live run with numbers matching the notebook exactly
(trough $1,562,800 wk 8 · headroom $631,300 · breach 20.2%); toggle transition is loud
(fan + ghost line + red breach callout); an edit made at the UI gate landed verbatim in
`final_report.json`; recommended-action sign-off captured; replay plays the captured run
with realistic pacing; workbook downloads via `/api/report`; zero console errors.

Launch: `Start Demo.command`, or `.claude/launch.json` config `cashflow-frontend` +
`python3 -m uvicorn backend.server:app --port 8000` from the project root.

## Hosted demo (mirrors hfma.robocfo.ai)

Deployed from `frontend/` as Vercel project **cashflow-cfo-demo** (team
glenn-hoppers-projects), static replay-only: no backend, so the header shows a single
**Play Demo** button that replays `public/replay_capture.json` (a pristine all-approved
run) and the workbook download serves `public/cashflow_13wk.xlsx`. Gated by
`PasswordGate` (access code `afp2026`, env `VITE_ACCESS_PASSWORD` in Vercel project
settings), `X-Robots-Tag: noindex`, deployment protection disabled to match HFMA.

- Live now: https://cashflow-cfo-demo-ez4uhbiu1-glenn-hoppers-projects.vercel.app
- **afp.robocfo.ai** is attached to the project; needs one GoDaddy DNS record
  (A · name `afp` · value `76.76.21.21`, same as the `hfma` record) to go live.
- Redeploy after changes: `cd frontend && vercel --prod --yes`. Refresh the demo run:
  copy new `output/replay_capture.json` + `output/cashflow_13wk.xlsx` into
  `frontend/public/` first.
