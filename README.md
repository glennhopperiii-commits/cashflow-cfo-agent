# Cascade Precision Products: 13-Week Cash Flow Agent

An agent harness for treasury forecasting, built for the AFP FP&A Virtual Summit 2026.
A Claude-powered agent builds the weekly 13-week cash flow for a synthetic LBO-owned
contract manufacturer: a deterministic roll-forward engine with revolver mechanics, a
Monte Carlo layer over collection timing and sales volume, a scenario engine, a blocking
human review gate, a complete audit trail, and a traditional TWCF workbook as the
deliverable.

The demo thesis: the single-point forecast passes the covenant with $631K to spare; the
distribution says there is a ~20% chance it does not. Deterministic control,
probabilistic reasoning.

## Layout

- `cashflow_harness/` — the harness as a pure, importable Python package (engine,
  Monte Carlo, tools, agent loop, audit logger, workbook report)
- `data/` — frozen synthetic dataset (seeded, reconciles to documented control totals;
  see `data/DATA_DESIGN.md`)
- `notebook/CashFlow_Agent.ipynb` — self-contained Colab walkthrough of the whole build
- `backend/` — FastAPI + WebSocket wrapper (imports the same package functions)
- `frontend/` — React demo UI: pipeline view, deterministic-to-probabilistic toggle,
  fan chart, revolver panel, covenant gauge, review gate, replay mode

## Run it

```bash
pip install -r requirements.txt        # needs ANTHROPIC_API_KEY in .env
python -m cashflow_harness.agent       # CLI mode
./Start\ Demo.command                  # full UI (backend :8000 + frontend :5173)
```

The hosted demo (static replay, no backend) deploys from `frontend/` via Vercel.
See `CLAUDE_CODE_BUILD_SPEC.md` for the full architecture.
