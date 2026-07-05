"""Generate notebook/CashFlow_Agent.ipynb — the self-contained Colab deliverable.

The notebook embeds every cashflow_harness module as a %%writefile cell, read
from the package source at build time. That keeps the no-drift rule: the code
in the notebook IS the code the Phase 2 server imports. After editing any
module, re-run:  python notebook/build_notebook.py
"""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PKG = ROOT / "cashflow_harness"

cells = []


def md(src):
    cells.append({"cell_type": "markdown", "id": f"cell-{len(cells)}", "metadata": {}, "source": src.splitlines(keepends=True)})


def code(src):
    cells.append({"cell_type": "code", "id": f"cell-{len(cells)}", "metadata": {}, "source": src.splitlines(keepends=True),
                  "outputs": [], "execution_count": None})


def module_cell(name):
    src = (PKG / name).read_text()
    code(f"%%writefile cashflow_harness/{name}\n{src}")


def data_cell(name):
    src = (ROOT / "data" / name).read_text()
    code(f"%%writefile data/{name}\n{src}")


# ============================================================================
# Title
# ============================================================================

md("""# Cascade Precision Products — 13-Week Cash Flow Agent

**A complete agent harness for treasury forecasting, in one notebook.** This file is
self-contained: run it top to bottom in Google Colab and it builds the harness, loads a
frozen synthetic dataset, runs the deterministic and probabilistic engines, drives a
Claude-powered agent through the full pipeline with a *real* human review gate, and hands
you the sponsor deliverable — a traditional 13-week cash flow workbook. The only thing you
supply is an `ANTHROPIC_API_KEY`.

## The story

Cascade Precision Products ($72M contract manufacturer of precision-machined aerospace,
defense, and industrial components; ~240 employees) was acquired ten weeks ago by
**Granite Peak Partners** in a leveraged buyout. The sponsor's first standing ask: a
weekly 13-week cash flow forecast with covenant visibility. Week one under new ownership —
prove you can see cash.

## The three layers this build teaches

| Layer | What it looks like here |
|---|---|
| **Governance** | A \\$1.5M operating cash floor, a \\$4.0M liquidity covenant tested at week 13, a human sign-off gate that actually blocks the pipeline, and a complete audit trail |
| **Finance** | Where is the trough, what threatens the covenant, and what should management do about it |
| **Capability** | A deterministic roll-forward engine, plus a Monte Carlo layer that turns a single-point forecast into a distribution |

## The punchline

**The single-point forecast passes the covenant with \\$631K to spare. The distribution
says there is a ~20% chance it doesn't.** Same data, same engine — one more question asked
of it. Deterministic control, probabilistic reasoning. That is the whole demo.

## A note for the FP&A reader: yes, this is an unusual way to build a TWCF

A traditional 13-week cash flow is a single spreadsheet: one number per week, receipts
penciled on due dates or the analyst's haircut, and a bottom line that either clears the
covenant or doesn't. This build departs from that in two ways, and both departures have
a serious claim to being the *better* practice:

**Departure 1 — collections are forecast from observed payment behavior, not stated
terms.** Every customer here carries its measured days-to-pay and the volatility around
it, and the forecast collects on behavior. Good treasury teams already do a version of
this (DSO-based timing, roll rates); this build just makes it explicit, per customer,
and auditable. Vantage Aerospace is on Net 45 and pays in 64 days — penciling its \\$2.1M
milestone on the due date isn't a forecast, it's a hope.

**Departure 2 — the forecast is a distribution, not a line.** This is the unusual part,
and the case for it:

1. **Headroom is not probability, and the point estimate hides the difference.** Two
   companies can both show \\$631K of week-13 headroom — one with sleepy, stable
   receivables, one with a fifth of its AR concentrated in a customer whose timing has
   started to wander. The classic TWCF cannot tell those companies apart. The
   distribution can: here, that same \\$631K carries a ~20% breach probability.
2. **Treasury decisions are bets, and you can't price a bet without odds.** Should you
   offer Vantage an early-pay incentive? Pre-clear a covenant waiver with the sponsor?
   Defer the machine deposit? Each mitigation has a cost, and comparing cost against
   "headroom feels thin" is vibes. Comparing it against "cuts breach probability from
   20% to 1.3%" is analysis.
3. **You already do this — just informally.** Every base/upside/downside scenario deck
   is three hand-picked draws from a distribution you carry in your head. Monte Carlo is
   the same idea done honestly: a thousand draws, sampled from each customer's *measured*
   payment variance instead of from judgment, with the correlations that actually break
   covenants (a slow payer is slow on all its invoices at once).
4. **It replaces sandbagging with auditable assumptions.** The classic way to express
   risk in a TWCF is silent conservatism — pencil the big collection a week late "to be
   safe." That distorts the base case, compounds invisibly across line items, and can't
   be audited. Here the base case stays honest (expected behavior) and the risk lives
   explicitly in the sigmas, which are measured from history and can be challenged line
   by line.
5. **The only reason TWCFs are single-point is that Excel made distributions expensive.**
   Banks and insurers have run their liquidity this way for decades (ALM, VaR). Once the
   roll-forward is a pure function instead of a spreadsheet, a thousand replays cost a
   fraction of a second. The marginal price of the honest answer has gone to zero.

And the part that should reassure rather than alarm: **the deterministic forecast is not
replaced.** It is still built, still reviewed, still the workbook that goes to the
sponsor, and it still ties out to the dollar. The probabilistic layer is one additional
question asked of the same engine. That is what "deterministic control, probabilistic
reasoning" means in practice.

## How this notebook is organized

- **Part 0** — setup (dependencies, Google Drive, and the API key)
- **Part 1** — the harness, module by module, then the frozen dataset. Each cell writes
  one file of the `cashflow_harness` package (or one data file) with an explanation of
  what it does and why. This is the same package a FastAPI + React demo UI wraps in
  Phase 2; the notebook and the UI run identical logic and cannot drift.
- **Part 2** — run it: verify the dataset, run the engines and scenarios, then the agent
  with the review gate, the audit trail, and the workbook.

> If you edit a module cell after running Part 2, restart the runtime
> (Runtime → Restart session) and re-run — Python caches imports.""")

# ============================================================================
# Part 0 — Setup
# ============================================================================

md("""---
# Part 0 · Setup

Two dependencies Colab doesn't ship with (`anthropic`, `python-dotenv`), an optional
Google Drive mount, and the API key.

**Where does the data come from?** It ships inside this notebook. Section 1.4 embeds
the frozen synthetic dataset — the exact files, byte for byte, that the demo was
calibrated and tested on (anchored to the 2026-08-21 Friday close; week 1 opens Monday
Aug 24). Nothing is generated at run time, nothing is uploaded, and nothing is read from
your machine. Part 2.1 verifies the dataset against its control totals before anything
else runs.

**Where does everything live?** Your choice, next cell. By default the whole project
(package, data, outputs) is created in a folder in your **Google Drive**, so the
generated data, the audit trail, and the 13-week workbook persist across Colab sessions
and are browsable in the Drive UI. Set `USE_DRIVE = False` to work in the runtime's
ephemeral disk instead (everything still runs; it just vanishes when the runtime
recycles).

The API key resolves in this order: environment variable → `.env` file → Colab secret
(the key icon in the left sidebar, name it `ANTHROPIC_API_KEY`) → an interactive prompt.
It is never hardcoded anywhere in this project — that is checklist item one for any
finance artifact that leaves your laptop.""")

code("""%pip install -q anthropic python-dotenv openpyxl""")

code("""# Choose where the project lives. USE_DRIVE = True mounts Google Drive and
# works from MyDrive/cashflow-cfo-agent so data and outputs persist across
# sessions. False = the runtime's ephemeral disk.
USE_DRIVE = True

import os
import pathlib

if USE_DRIVE:
    try:
        from google.colab import drive  # type: ignore
        drive.mount("/content/drive")
        workdir = "/content/drive/MyDrive/cashflow-cfo-agent"
        os.makedirs(workdir, exist_ok=True)
        os.chdir(workdir)
    except ImportError:
        print("Not running in Colab — staying in the current directory.")

os.makedirs("cashflow_harness", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("output", exist_ok=True)
print("Project home:", pathlib.Path.cwd())""")

code("""# API key: env var -> .env -> Colab secret -> prompt. Never hardcoded.
if not os.getenv("ANTHROPIC_API_KEY"):
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
if not os.getenv("ANTHROPIC_API_KEY"):
    try:
        from google.colab import userdata  # type: ignore
        os.environ["ANTHROPIC_API_KEY"] = userdata.get("ANTHROPIC_API_KEY")
    except Exception:
        import getpass
        os.environ["ANTHROPIC_API_KEY"] = getpass.getpass("ANTHROPIC_API_KEY: ")
print("API key loaded:", "yes" if os.getenv("ANTHROPIC_API_KEY") else "NO — the agent run in Part 2 will fail")""")

# ============================================================================
# Part 1 — The harness
# ============================================================================

md("""---
# Part 1 · The harness, module by module

Nine files. Read them in order and you have read the whole system. The design rule that
matters most: **every function is pure and importable.** The notebook calls them here;
the Phase 2 demo server imports the same functions unchanged. If a number ever differs
between the notebook and the UI, the wrapper is wrong, not the engine.""")

md("""## 1.1 · `config.py` — the governance rails and the agent's charter

Everything the credit agreement and treasury policy fix in advance lives here as named
constants: the \\$1.5M operating floor, the \\$4.0M covenant and its week-13 test, the
\\$250K draw increment, the sweep buffer, the Monte Carlo seed (reproducibility is a
governance feature — the same forecast twice gives the same answer).

It also holds the **system prompt**: the agent's role (treasury/FP&A analyst at Cascade,
newly LBO'd), the ten-tool workflow it must follow, and the writing rules for the
commentary (cite the driver behind every number, distinguish timing from structural,
no speculation beyond the data). The harness is model-agnostic — `MODEL` is one string,
swappable to Opus or a future model without touching anything else.""")

module_cell("config.py")

md("""## 1.2 · `engine.py` — the deterministic core

A pure function: position + dated receipts + dated disbursements in, 13 weekly rows out.
Per week: beginning cash + receipts − disbursements = pre-revolver cash, then the
revolver mechanics every treasury team runs by hand:

- **Below the \\$1.5M floor** → auto-draw the revolver (rounded up to \\$250K increments,
  capped at availability) to restore it.
- **Comfortably above the floor** (floor + \\$500K buffer) → sweep the excess to pay the
  revolver down.

It reports, per week: receipts, disbursements, pre-revolver cash, draw/paydown, revolver
balance, ending cash, and **covenant liquidity** (cash + undrawn availability) — plus the
trough week and week-13 covenant headroom.

Two design points worth pausing on:

1. **Collections are forecast from behavior, not stated terms.** `expected_pay_date()`
   uses each customer's observed days-to-pay. Vantage Aerospace is on Net 45 and pays in
   ~64 days; that 19-day gap is what moves its \\$2.1M milestone from the week-4 pencil to
   a week-7 landing.
2. **No side effects, no randomness, no I/O.** The Monte Carlo layer calls this function
   a thousand times; purity is what makes that a one-liner.""")

module_cell("engine.py")

md("""## 1.3 · `montecarlo.py` — the probabilistic layer

This is the module that makes the build unusual, so name the logic plainly: the
deterministic forecast in 1.2 collects every invoice at its customer's *average*
observed behavior. But nobody pays at their average every time — the average came with
a variance, measured from the same history. If the mean of observed behavior belongs in
the forecast, its variance does too. Refusing the variance doesn't make the risk go
away; it just makes it invisible.

So each iteration re-answers one question: *what if customers pay the way they actually
pay, and the ramp bills what it actually bills?* Then it re-runs the deterministic
engine — a thousand times.

The sampling model is deliberately structured, not just noise:

- **Collection timing** — each customer gets one *systematic* shift per iteration (a
  customer that pays late pays late on every invoice; 60% of its sigma) plus
  *idiosyncratic* per-invoice noise (80% of sigma). The split preserves total observed
  variance while creating the correlated risk that actually threatens covenants.
- **Sales volume** — each week's new billings draw around the forecast with that week's
  sigma (rising 10% → 15% into the ramp, because new programs are less certain).
- **Collection tranches** — a billing week doesn't collect as one lump; it spreads
  25/50/25 around the blended lag. That keeps the exposure at the week-13 boundary smooth
  and the simulation median centered on the deterministic path.

Outputs: P10/P50/P90 bands per week, the trough distribution, week-13 liquidity
percentiles, **P(covenant breach at week 13)** — the number that changes the meeting —
and P(the floor cannot be restored within the revolver limit), which is the treasury
definition of real trouble.""")

module_cell("montecarlo.py")

md("""## 1.4 · The fixed dataset — Cascade Precision's book of record

Synthetic, but not arbitrary — and **frozen**. These are the exact files the demo was
calibrated and tested against, embedded byte for byte: they were produced once by the
repo's seeded generator (`cashflow_harness/data_gen.py`, anchored to the 2026-08-21
Friday close) and never regenerated at run time, so there is no drift risk between what
was tested and what runs. The control totals: open AR of exactly \\$19.3M across 122
invoices with **Vantage Aerospace at \\$4.2M (21.8%)**, open AP of exactly \\$8.7M across
90 bills, every scheduled one-timer in its week, and trailing 4-week actuals exactly
6.0% under the prior forecast.

Five stories are baked in for the agent to surface:

1. **The Vantage term stretch** — the largest customer slid from Net 45 to ~64 days;
   a \\$2.1M collection penciled for week 4 now lands week 7.
2. **The growth working-capital build** — ramp material buys and a second shift hit
   weeks 3–7, ahead of billings that collect weeks 9–13 and beyond.
3. **Lumpy scheduled outflows** — insurance (wk 5), capex deposit (wk 6), earn-out
   (wk 9), tax (wk 10), \\$2.2M debt service (wk 13).
4. **A tight-but-passing covenant** — trough ~\\$1.56M in week 8, week-13 headroom ~\\$631K.
5. **The probabilistic reversal** — P50 passes, P10 breaches; ~20% breach probability.

Seven files: the treasury context memo, the facility terms, the AR and AP ledgers (one
record per line), the fixed disbursement schedule, the sales forecast, and the trailing
actuals. Part 2.1 verifies every control total before anything else runs; the design
reference lives in the repo as `data/DATA_DESIGN.md`.""")

data_cell("company_context.md")
data_cell("facility_terms.json")
data_cell("ar_open_invoices.json")
data_cell("ap_open_bills.json")
data_cell("fixed_schedule.csv")
data_cell("sales_forecast.csv")
data_cell("historical_actuals.csv")

md("""## 1.5 · `logger.py` — the audit trail

Small on purpose. Every pipeline event — every tool call, its inputs, its outputs, the
agent's narration, the reviewer's decisions — lands in an append-only list with a UTC
timestamp, then persists to `output/audit_log.json` and `output/replay_capture.json`
(the replay file is the live-demo safety net for Phase 2). When someone asks "where did
this number come from" six weeks later, this file is the answer.""")

module_cell("logger.py")

md("""## 1.6 · `tools.py` — the agent's tool belt

Ten tools in three patterns:

- **Data readers** (1–3): load the facility, the receivables (with per-customer behavior
  stats and term-stretch flags), and the payables/fixed schedule. They return structured
  summaries, not raw dumps — the tool shapes what the model attends to.
- **Computation tools** (4–7): the deterministic forecast, the Monte Carlo, the scenario
  engine, and the trailing variance bridge. `run_scenario` supports single what-ifs
  (slip a customer, accelerate a collection, defer an item, flex sales, stretch AP) and
  a `driver_sweep` that ranks what moves week-13 headroom most — the tornado.
- **Pass-through and governance tools** (8–10): `draft_cash_narrative` forces the
  narrative into a validated structure (so it lands in the audit trail, not just chat
  text), `submit_for_review` is the mandatory human gate, and `log_output` writes the
  final record.

A finance subtlety the scenario engine makes teachable: covenant liquidity
(cash + availability) is *invariant* to revolver draws and sweeps, so **only flows that
cross the week-13 boundary move deterministic headroom**. Deferring the capex deposit
two weeks does nothing; deferring it past the test date, or pulling Vantage collections
back inside the quarter, moves real money. Watch the agent discover this in Part 2.""")

module_cell("tools.py")

md("""## 1.7 · `tool_schemas.py` — the contract with the model

The Anthropic tool definitions, one per function in `tools.py`. Descriptions carry the
domain intent ("the number that changes the meeting"), and the pass-through schemas force
structure: the narrative must arrive as sections with confidence levels and open flags,
plus a single recommended action with a rationale and quantified effect. Structured
output isn't cosmetic — it is what makes the review gate and the audit trail possible.""")

module_cell("tool_schemas.py")

md("""## 1.8 · `agent.py` — the loop and the gate

The standard Anthropic tool-use loop: call the model, execute each requested tool, feed
results back, repeat until it stops. Two things make it a *harness* rather than a script:

1. **The human gate is a callback.** When the agent calls `submit_for_review`, the loop
   emits a `review_requested` event and calls whatever `review_handler` you passed in.
   This notebook passes an in-cell prompt (approve / edit / reject per section). Phase 2
   passes a WebSocket handler that blocks until the frontend responds. No handler means
   auto-approve (CLI smoke tests). Same loop, three gates.
2. **Everything is an event.** `step_started`, `step_completed`, `agent_text`,
   `review_requested`, `pipeline_complete`, `report_generated` — printed here, streamed
   over a WebSocket in Phase 2, and logged to the audit trail either way.

After the loop completes, the harness writes the sponsor deliverable (the 13-week
workbook) automatically — inside a try/except, because a report bug must never kill a
pipeline run.""")

module_cell("agent.py")

md("""## 1.9 · `report.py` — the sponsor deliverable

Agents that end in JSON don't get invited back. This module renders the classic FP&A
artifact — a **traditional 13-week cash flow**: line items down the side, weeks across
the top. Receipts by customer (top 5 named, the \\$2.1M Vantage milestone visible in its
week-7 column), disbursements by category, cash-before-revolver mechanics, draws and
paydowns, and the revolver/covenant block ending in a PASS/BREACH flag.

`build_forecast_grid()` asserts every line ties to the engine's weekly totals **to the
dollar** — the spreadsheet cannot drift from what the agent analyzed. `write_xlsx()`
always works (openpyxl); `to_google_sheet()` publishes a real Google Sheet, which in
Colab needs nothing but one auth popup.""")

module_cell("report.py")

md("""### Import the package we just wrote""")

code("""import pathlib
import sys

if str(pathlib.Path.cwd()) not in sys.path:
    sys.path.insert(0, str(pathlib.Path.cwd()))

# __init__.py for the package
init_src = '\"\"\"Cascade Precision Products 13-week cash flow agent harness.\"\"\"\\n'
pathlib.Path("cashflow_harness/__init__.py").write_text(init_src)

from cashflow_harness import config
print(f"cashflow_harness ready · model = {config.MODEL} · MC = {config.MC_ITERATIONS} iterations, seed {config.MC_SEED}")""")

# ============================================================================
# Part 2 — Run it
# ============================================================================

md("""---
# Part 2 · Run it

Part 1 was the machine. Part 2 turns it on: generate the company, drive each engine by
hand so you can see what the agent will see, then hand the keys to the agent — with you
at the review gate.""")

md("""## 2.1 · Verify the fixed dataset

Trust, then verify. Before any engine runs, confirm the embedded files match every
control total the demo was calibrated against: AR \\$19.3M with Vantage at exactly
\\$4.2M, AP \\$8.7M across 90 bills, each one-timer in its scheduled week, and the
trailing 4-week miss at -6.0%. If any check fails, stop — something touched the data.""")

code("""import csv
import json

def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL':4}  {name}  {detail}")
    assert ok, f"Dataset verification failed: {name}"

with open("data/ar_open_invoices.json") as f:
    invoices = json.load(f)
with open("data/ap_open_bills.json") as f:
    bills = json.load(f)
with open("data/facility_terms.json") as f:
    fac = json.load(f)
with open("data/fixed_schedule.csv") as f:
    fixed = list(csv.DictReader(f))
with open("data/historical_actuals.csv") as f:
    hist = list(csv.DictReader(f))

ar_total = sum(i["amount"] for i in invoices)
vantage = sum(i["amount"] for i in invoices if i["customer"] == "Vantage Aerospace")
ap_total = sum(b["amount"] for b in bills)

check("Open AR = $19,300,000", ar_total == 19_300_000, f"${ar_total:,}")
check("122 invoices", len(invoices) == 122, str(len(invoices)))
check("Vantage = $4,200,000 (21.8%)", vantage == 4_200_000, f"${vantage:,} ({vantage/ar_total:.1%})")
check("Open AP = $8,700,000 / 90 bills", ap_total == 8_700_000 and len(bills) == 90, f"${ap_total:,} / {len(bills)}")
check("Anchor: 2026-08-21 close, week 1 = 2026-08-24",
      fac["as_of_close"] == "2026-08-21" and fac["week1_monday"] == "2026-08-24")
check("Beginning cash / revolver / covenant",
      fac["beginning_cash"] == 2_400_000 and fac["revolver_drawn"] == 6_000_000
      and fac["covenant"]["threshold"] == 4_000_000)

one_timers = {r["category"]: int(r["week"]) for r in fixed
              if r["category"] in ("insurance", "capex", "acquisition", "tax")}
check("One-timers in weeks 5/6/9/10",
      one_timers == {"insurance": 5, "capex": 6, "acquisition": 9, "tax": 10}, str(one_timers))
ds = [r for r in fixed if r["category"] == "debt service"]
check("Debt service $2.2M in week 13",
      sum(float(r["amount"]) for r in ds) == 2_200_000 and all(int(r["week"]) == 13 for r in ds))

fc = sum(float(r["forecast_collections"]) for r in hist)
ac = sum(float(r["actual_collections"]) for r in hist)
check("Trailing 4-week miss = -6.0%", abs((ac - fc) / fc + 0.06) < 0.001, f"{(ac - fc) / fc:.1%}")

print("\\nDataset verified — this is the exact book the demo was calibrated on.")""")

md("""## 2.2 · The position

Tool 1: the facility. Beginning cash of \\$2.4M, a \\$15M revolver with \\$6M drawn
(\\$9M availability, \\$11.4M beginning liquidity), the \\$1.5M floor, the \\$4.0M
week-13 covenant, and \\$2.2M of quarterly debt service due the same week the covenant
is tested. This is the governance frame every later number lives inside.""")

code("""import json
from cashflow_harness import tools

facility = tools.load_facility_and_position()
print(json.dumps(facility, indent=2))""")

md("""## 2.3 · Receivables and payables — the raw material

Two things to watch in the receivables: **concentration** (top 5 ≈ 60% of AR) and the
**term-stretch flags** — customers whose observed behavior has drifted well past stated
terms. Vantage is the one that matters: 22% of AR, paying 19 days past terms. The
payables side shows the ramp: AP due dates heaviest in weeks 3–7, forecast material
purchases building through the quarter, payroll stepping up when the second shift loads
in week 5, and the five one-timers.""")

code("""import pandas as pd

ar = tools.load_receivables()
print(f"Open AR ${ar['total_open_ar']:,} across {ar['invoice_count']} invoices | top-5 concentration {ar['top5_concentration']:.0%}")
print(f"Term-stretch flags: {', '.join(ar['flagged_term_stretch'])}\\n")

cust = pd.DataFrame(ar["customers"])
cust["open_ar"] = cust["open_ar"].map("{:,.0f}".format)
cust[["customer", "terms", "days_to_pay", "stretch_days_vs_terms", "open_ar", "share_of_ar", "term_stretch_flag"]]""")

code("""ap = tools.load_payables_and_fixed()
print(f"Open AP ${ap['total_open_ap']:,} across {ap['ap_bill_count']} bills\\n")
print("One-time scheduled outflows:")
for item in ap["one_time_items"]:
    print(f"  wk {item['week']:>2}  ${item['amount']:>12,.0f}  {item['item']}")
print("\\nDiscretionary (deferrable) items:")
for item in ap["discretionary_items"]:
    print(f"  wk {item['week']:>2}  ${item['amount']:>12,.0f}  {item['item']}")
pd.DataFrame(ap["weekly_disbursement_schedule"]).fillna(0).astype(int)""")

md("""## 2.4 · The deterministic forecast

Read the story in the table: the glide down through week 4 (the \\$2.1M Vantage
collection that *isn't there*), draws beginning week 5 as the insurance premium and ramp
buys hit, the **trough of ~\\$1.56M in week 8** right after the \\$250K week-7 draw, the
earn-out draw in week 9, and the \\$2.25M debt-service draw in week 13 that leaves
**\\$631,300 of covenant headroom**. Passes. Thin, but passes — hold that thought for 2.5.""")

code("""det = tools.build_deterministic_forecast()

def acct(x):
    return f"({abs(x):,.0f})" if x < 0 else f"{x:,.0f}"

table = pd.DataFrame(det["weeks"])
display_cols = ["week", "receipts", "disbursements", "net_flow", "pre_revolver_cash",
                "revolver_draw", "revolver_paydown", "revolver_balance", "ending_cash", "covenant_liquidity"]
styled = table[display_cols].copy()
for c in display_cols[1:]:
    styled[c] = styled[c].map(acct)
print(f"Trough: ${det['trough_cash']:,.0f} in week {det['trough_week']}")
print(f"Week-13 covenant liquidity: ${det['test_week_liquidity']:,.0f} vs ${det['covenant_threshold']:,.0f} threshold")
print(f"Covenant headroom: ${det['covenant_headroom']:,.0f}  →  {'PASS' if det['covenant_pass'] else 'BREACH'}")
styled""")

md("""## 2.5 · The Monte Carlo — where the demo turns

Same engine, 1,000 seeded iterations over collection timing and sales volume. The
deterministic line said *pass, \\$631K to spare*. The distribution says **the P10 path
breaches at week 13** and puts breach probability around **20%**. Nothing about the data
changed. The left chart shows weekly ending cash against the \\$1.5M floor; the right
shows covenant liquidity against the \\$4.0M threshold — the fan crossing that red line
is the picture that changes the sponsor conversation.

If the distribution idea still feels exotic, translate the output into the language any
treasurer already uses: *"we pass the covenant in the base case, but if Vantage and one
or two others drift the way they've been drifting, roughly one quarter in five ends in
an event of default."* That sentence was always true. The classic TWCF just couldn't
say it with a number attached — and the number is what lets you price the fix (section
2.6: accelerating Vantage to terms takes the odds from 20% to ~1%).""")

code("""mc = tools.run_monte_carlo()

print(f"Iterations: {mc['iterations']}  (seed {mc['seed']}, reproducible)")
print(f"P(covenant breach at week 13):        {mc['p_covenant_breach']:.1%}")
print(f"P(floor unrestorable within revolver): {mc['p_below_floor_any_week']:.1%}")
print(f"Week-13 liquidity  P10 ${mc['test_week_liquidity_p10']:,}   P50 ${mc['test_week_liquidity_p50']:,}   P90 ${mc['test_week_liquidity_p90']:,}")
print(f"Trough cash        P10 ${mc['trough_cash_p10']:,}   P50 ${mc['trough_cash_p50']:,}   P90 ${mc['trough_cash_p90']:,}")""")

code("""import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

SLATE, AMBER, GREEN, RED, INK = "#3B5998", "#D97706", "#16A34A", "#DC2626", "#1E293B"
weeks = mc["weeks"]
det_cash = [w["ending_cash"] for w in det["weeks"]]
det_liq = [w["covenant_liquidity"] for w in det["weeks"]]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), facecolor="white")

# Left: ending cash fan with the operating floor
ax1.fill_between(weeks, mc["ending_cash_p10"], mc["ending_cash_p90"],
                 color=SLATE, alpha=0.18, label="P10–P90 band")
ax1.plot(weeks, mc["ending_cash_p50"], color=SLATE, lw=2.4, label="P50 (median)")
ax1.plot(weeks, det_cash, color=INK, lw=2, ls="--", label="Deterministic")
ax1.axhline(mc["operating_floor"], color=AMBER, lw=2, ls=":")
ax1.annotate("Operating floor $1.5M", (1, mc["operating_floor"]), xytext=(0, 8),
             textcoords="offset points", color=AMBER, fontweight="bold")
ax1.set_title("Weekly ending cash — deterministic vs. P10–P90 fan", color=INK, fontsize=13, fontweight="bold")
ax1.set_xlabel("Week"); ax1.set_xticks(weeks)

# Right: covenant liquidity fan with the threshold
ax2.fill_between(weeks, mc["liquidity_p10"], mc["liquidity_p90"],
                 color=SLATE, alpha=0.18, label="P10–P90 band")
ax2.plot(weeks, mc["liquidity_p50"], color=SLATE, lw=2.4, label="P50 (median)")
ax2.plot(weeks, det_liq, color=INK, lw=2, ls="--", label="Deterministic")
ax2.axhline(mc["covenant_threshold"], color=RED, lw=2, ls=":")
ax2.annotate("Covenant threshold $4.0M", (1, mc["covenant_threshold"]), xytext=(0, 8),
             textcoords="offset points", color=RED, fontweight="bold")
ax2.annotate(f"P(breach wk 13) = {mc['p_covenant_breach']:.0%}",
             (13, mc["liquidity_p10"][-1]), xytext=(-130, -34), textcoords="offset points",
             color=RED, fontsize=13, fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.4", fc="#FEF2F2", ec=RED))
ax2.set_title("Covenant liquidity (cash + availability)", color=INK, fontsize=13, fontweight="bold")
ax2.set_xlabel("Week"); ax2.set_xticks(weeks)

for ax in (ax1, ax2):
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"${v/1e6:.1f}M"))
    ax.legend(loc="upper right", frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#F1F5F9")
plt.tight_layout()
plt.show()""")

md("""## 2.6 · Scenarios — what actually moves the covenant

The driver sweep, ranked by impact on week-13 headroom. The finance lesson falls out of
the mechanics: covenant liquidity is invariant to revolver activity, so **only flows that
cross the week-13 boundary move deterministic headroom**. Deferring the capex deposit two
weeks (6 → 8) does *nothing* — the revolver was already defending the floor; the deferral
just changes which week draws. Deferring it *past the test date* adds \\$800K. And
accelerating Vantage back to its Net 45 terms is the biggest lever on the board: +\\$1.1M
of headroom, breach probability from 20% to ~1%.""")

code("""sweep = tools.run_scenario(scenario_type="driver_sweep")
b = sweep["baseline"]
print(f"Baseline: trough ${b['trough_cash']:,.0f} wk {b['trough_week']} | headroom ${b['covenant_headroom']:,.0f} | P(breach) {b['p_covenant_breach']:.1%}\\n")
rows = pd.DataFrame(sweep["sweep"])[["label", "delta_covenant_headroom", "delta_trough_cash", "delta_p_breach", "p_covenant_breach"]]
rows""")

code("""fig, ax = plt.subplots(figsize=(11, 4.8), facecolor="white")
data = sorted(sweep["sweep"], key=lambda r: r["delta_covenant_headroom"])
labels = [r["label"] for r in data]
vals = [r["delta_covenant_headroom"] for r in data]
colors = [GREEN if v > 0 else (RED if v < 0 else "#94A3B8") for v in vals]
ax.barh(labels, vals, color=colors)
for i, (v, r) in enumerate(zip(vals, data)):
    ax.text(v + (40_000 if v >= 0 else -40_000), i, f"P(breach) {r['p_covenant_breach']:.0%}",
            va="center", ha="left" if v >= 0 else "right", fontsize=10, color=INK)
ax.axvline(0, color=INK, lw=1)
ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"${v/1e6:+.1f}M"))
ax.set_title("Driver tornado — change to week-13 covenant headroom", color=INK, fontsize=13, fontweight="bold")
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout(); plt.show()""")

md("""## 2.7 · Trailing variance — why we trust behavior-based timing

The bridge for the last 4 weeks: collections came in 6% under the prior forecast, and
**87% of the miss is one slipped Vantage invoice** — timing on a fully collectible
receivable, not volume, not credit. That is the evidence for forecasting Vantage at 64
days instead of Net 45, and it is the same behavior driving the week-4 → week-7 slip on
the \\$2.1M milestone. A forecast that can explain its own last miss earns the right to
be believed about the next thirteen weeks.""")

code("""var = tools.compute_variance()
print(f"Trailing {var['trailing_weeks']} weeks: forecast ${var['forecast_collections_total']:,} vs actual ${var['actual_collections_total']:,}")
print(f"Miss: ${var['total_variance']:,}  ({var['variance_pct_of_forecast']:.1%})")
print(f"Attribution — Vantage timing: ${var['attribution']['vantage_timing']:,} ({var['attribution']['vantage_share_of_miss']:.0%} of miss) | all other: ${var['attribution']['all_other']:,}")
pd.DataFrame(var["weekly_bridge"])""")

md("""## 2.8 · The agent run — with a real human gate

Everything above was us driving the tools by hand. Now the agent drives: same functions,
Claude decides the sequence, reads the results, runs the scenarios it judges relevant,
and drafts the treasury narrative. Two governance features to watch:

1. **The review gate blocks.** When the agent calls `submit_for_review`, the pipeline
   stops and this cell prompts *you* to approve / edit / reject each narrative section
   and sign off on the recommended action. Your edits become the final record. The agent
   proposes; you dispose.
2. **Everything is logged.** Every tool call, input, output, and review decision lands
   in `output/audit_log.json`.

First, the two callbacks: the review handler (the notebook's implementation of the gate —
Phase 2 swaps in a WebSocket version, same agent loop) and a pretty-printer for the
event stream.""")

code("""# The notebook implementation of the human gate: prompt in-cell for each section.
# Phase 2 swaps this callback for a WebSocket gate in the demo UI. Same agent loop.

async def notebook_review_handler(payload):
    print("=" * 72)
    print("HUMAN REVIEW GATE — the pipeline is paused until you respond")
    print("=" * 72)
    if payload["message"]:
        print(f"\\nAgent's message to you:\\n{payload['message']}\\n")

    decisions = []
    for s in payload["sections"]:
        print("-" * 72)
        print(f"SECTION: {s['title']}   [confidence: {s['confidence']}]")
        print(s["content"])
        for flag in s.get("open_flags", []):
            print(f"  ⚑ open flag: {flag}")
        while True:
            choice = input("[a]pprove / [e]dit / [r]eject > ").strip().lower()
            if choice in ("a", "e", "r"):
                break
        if choice == "a":
            decisions.append({"section_title": s["title"], "action": "approved",
                              "edited_content": None, "notes": ""})
        elif choice == "e":
            edited = input("Replacement text > ").strip()
            decisions.append({"section_title": s["title"], "action": "edited",
                              "edited_content": edited, "notes": "Edited at notebook gate."})
        else:
            reason = input("Rejection reason > ").strip()
            decisions.append({"section_title": s["title"], "action": "rejected",
                              "edited_content": None, "notes": reason})

    ra = payload["recommended_action"]
    print("-" * 72)
    print(f"RECOMMENDED ACTION: {ra.get('action', '')}")
    print(f"Rationale: {ra.get('rationale', '')}")
    if "expected_headroom_effect" in ra:
        print(f"Expected headroom effect: ${ra['expected_headroom_effect']:,.0f}")
    while True:
        choice = input("Sign off on the recommended action? [a]pprove / [r]eject > ").strip().lower()
        if choice in ("a", "r"):
            break
    disposition = {"action": ra.get("action", ""),
                   "disposition": "approved" if choice == "a" else "rejected",
                   "notes": "" if choice == "a" else input("Reason > ").strip()}
    print("=" * 72)
    return {"decisions": decisions, "recommended_action_disposition": disposition}""")

code("""# Pretty printer for pipeline events as they stream past.
STEP_LABELS = {
    "load_facility_and_position": "1 · Position and facility",
    "load_receivables": "2 · Receivables",
    "load_payables_and_fixed": "3 · Payables and fixed items",
    "build_deterministic_forecast": "4 · Deterministic forecast",
    "run_monte_carlo": "5 · Monte Carlo",
    "run_scenario": "6 · Scenario",
    "compute_variance": "7 · Trailing variance",
    "draft_cash_narrative": "8 · Treasury narrative",
    "submit_for_review": "9 · Human review",
    "log_output": "10 · Audit log",
}

async def notebook_callback(event, data):
    if event == "agent_text":
        print(f"\\n💬 {data['text']}")
    elif event == "step_started":
        print(f"\\n▶ {STEP_LABELS.get(data['step'], data['step'])}")
    elif event == "step_completed":
        out = data["output"]
        step = data["step"]
        if step == "build_deterministic_forecast":
            print(f"   trough ${out['trough_cash']:,.0f} (wk {out['trough_week']}) | headroom ${out['covenant_headroom']:,.0f}")
        elif step == "run_monte_carlo":
            print(f"   P(breach) {out['p_covenant_breach']:.1%} | wk-13 liq P10 ${out['test_week_liquidity_p10']:,}")
        elif step == "run_scenario":
            if "sweep" in out:
                top = out["sweep"][0]
                print(f"   sweep: biggest driver → {top['label']} (Δ headroom ${top['delta_covenant_headroom']:,.0f})")
            elif "result" in out:
                r = out["result"]
                print(f"   Δ headroom ${r['delta_covenant_headroom']:,.0f} | P(breach) {r['p_covenant_breach']:.1%}")
        elif step == "compute_variance":
            print(f"   miss ${out['total_variance']:,} ({out['variance_pct_of_forecast']:.1%}), Vantage {out['attribution']['vantage_share_of_miss']:.0%} of it")
        elif step == "draft_cash_narrative":
            print(f"   {out.get('section_count', '?')} sections drafted")
        elif step == "log_output":
            print(f"   audit written → {out.get('path', '')}")
        elif "error" in out:
            print(f"   ⚠ {out['error']}")
    elif event == "report_generated":
        print(f"\\n📊 13-week cash flow workbook written → {data['path']}")""")

code("""from cashflow_harness.agent import run_agent
from cashflow_harness.logger import AuditLogger

audit = AuditLogger()
result = await run_agent(
    ws_callback=notebook_callback,
    review_handler=notebook_review_handler,
    audit_logger=audit,
)
print(f"\\nPipeline status: {result['status']}")""")

md("""## 2.9 · The final narrative and the audit trail

What you approved (or edited) at the gate is the record that goes to Granite Peak. The
audit log holds every tool call, every number, and every review decision — the answer to
"where did this figure come from" six weeks from now.""")

code("""state = result["state"]
ra = state.get("recommended_action_disposition", {})
print("FINAL TREASURY NARRATIVE — as reviewed")
print("=" * 72)
for s in state.get("final_sections", []):
    print(f"\\n## {s['title']}  [{s['reviewer_action']}]")
    print(s["final_content"])
print("\\n" + "=" * 72)
print(f"RECOMMENDED ACTION [{ra.get('disposition', '?')}]: {ra.get('action', '')}")
print(f"\\nRun summary: {state.get('report_summary', '')}")""")

code("""audit_path = pathlib.Path("output") / "audit_log.json"
with open(audit_path) as f:
    trail = json.load(f)
from collections import Counter
counts = Counter(e["event"] for e in trail["events"])
print(f"Audit trail: {trail['event_count']} events → {audit_path}")
for event, n in counts.most_common():
    print(f"  {event:>20}: {n}")
print("\\nEvery number in the narrative traces to a logged tool call. That is the point.")""")

md("""## 2.10 · The sponsor deliverable — a traditional 13-week TWCF spreadsheet

Numbers in a JSON payload are for machines. What goes to Granite Peak is the classic FP&A
artifact: line items down the side, weeks across the top — receipts by customer,
disbursements by category, cash before revolver, draws and paydowns, ending cash, and the
covenant block with a PASS/BREACH flag. The agent run above already wrote the Excel
version automatically (the `report_generated` event); this cell rebuilds it so you can
inspect the grid, and the next one publishes it as a real Google Sheet.""")

code("""from cashflow_harness.report import build_forecast_grid, write_xlsx

grid = build_forecast_grid()
path = write_xlsx(grid)   # idempotent — the agent run already wrote this
print(f"Workbook: {path}")
print(f"Trough ${grid['trough_cash']:,.0f} in week {grid['trough_week']} | "
      f"week-13 covenant test: {'PASS' if grid['covenant_pass'] else 'BREACH'}\\n")

# Preview the spine of the sheet
key_rows = [r for r in grid["rows"] if r["values"] is not None and
            (r["style"] == "total" or r["label"] in ("Beginning cash", "Revolver balance", "Undrawn availability"))]
pd.DataFrame([
    {"line item": r["label"], **{f"W{i+1}": f"{v:,.0f}" for i, v in enumerate(r["values"])}}
    for r in key_rows
])""")

code("""# Publish as a real Google Sheet. In Colab this needs one auth popup and
# nothing else (gspread is preinstalled). Outside Colab, the Excel file above
# is the deliverable — upload it to Drive or install gspread + google-auth.
try:
    from google.colab import auth  # type: ignore
    auth.authenticate_user()
    from cashflow_harness.report import to_google_sheet
    url = to_google_sheet(grid)
    print("Google Sheet created:", url)
except ImportError:
    print("Not running in Colab — skipping the Google Sheet, the .xlsx above is the deliverable.")""")

md("""---
# What Phase 2 adds

Nothing to the logic. A FastAPI server wraps `run_agent` with a WebSocket review gate,
and a React frontend renders the pipeline spine, the **deterministic ↔ probabilistic
toggle** (the single most important interaction in the demo), the P10–P90 fan chart, the
revolver utilization panel, the covenant headroom gauge, the variance waterfall, the
driver tornado, and this same review workspace. The notebook and the UI import the same
`cashflow_harness` functions — they cannot drift.

*This notebook is generated from the package source by `notebook/build_notebook.py`;
the module cells above are byte-identical to the files the Phase 2 server imports.*""")

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11.0"},
        "colab": {"provenance": []},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

out = ROOT / "notebook" / "CashFlow_Agent.ipynb"
with open(out, "w") as f:
    json.dump(nb, f, indent=1)
print(f"wrote {out} with {len(cells)} cells")
