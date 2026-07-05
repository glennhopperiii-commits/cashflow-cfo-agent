"""Anthropic tool definitions for the cash flow agent.

Names and parameters mirror the functions in tools.py one for one. The
pass-through tools (draft_cash_narrative) force structured output so the
narrative is captured in the audit trail rather than living only in
free-form model text.
"""

TOOLS = [
    {
        "name": "load_facility_and_position",
        "description": "Load the opening treasury position and facility terms: beginning cash, revolver limit / drawn / availability, the operating cash floor and sweep policy, the liquidity covenant (threshold, test week, consequence), and the term loan debt service schedule.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "load_receivables",
        "description": "Load open accounts receivable: per-customer subtotals with share of AR, stated terms versus observed days-to-pay (with sigma), concentration, the largest open invoices, and expected collections by week based on observed payment behavior. Customers whose payment behavior has stretched well past terms are flagged.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "load_payables_and_fixed",
        "description": "Load scheduled disbursements: open AP bucketed by due week, plus the fixed schedule (payroll, rent, benefits, utilities, one-time items, debt service, forecast ramp material purchases) by week and category. Returns one-time items and the discretionary list separately.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "build_deterministic_forecast",
        "description": "Run the deterministic 13-week cash roll-forward with revolver mechanics (auto-draw to the floor, sweep above floor + buffer). Returns the weekly table (receipts, disbursements, pre-revolver cash, draws/paydowns, revolver balance, ending cash, covenant liquidity), the trough week and amount, and week-13 covenant headroom.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "run_monte_carlo",
        "description": "Run the probabilistic layer: resample every invoice's pay timing from the customer's observed behavior and every week's new billings from the forecast sigma, then re-run the deterministic engine per iteration. Returns P10/P50/P90 ending cash and liquidity by week, the trough distribution, week-13 liquidity percentiles, the probability the floor cannot be restored within the revolver limit, and the probability of a week-13 covenant breach. Seeded and reproducible.",
        "input_schema": {
            "type": "object",
            "properties": {
                "iterations": {"type": "integer", "description": "Number of iterations (default 1000)."},
                "seed": {"type": "integer", "description": "Random seed (default 42, the reproducible demo seed)."},
            },
            "required": [],
        },
    },
    {
        "name": "run_scenario",
        "description": "Run a what-if against the base forecast and report the new trough, week-13 headroom, and breach probability with deltas. Use scenario_type 'driver_sweep' (no other arguments) to run the standard tornado sweep ranking what moves week-13 covenant headroom most. Other types: 'slip_collections' (customer optional, days required: everyone or one customer pays N days later), 'accelerate_collection' (customer and days required: pin a customer's collections to N days, e.g. Vantage back to 45-day terms), 'defer_item' (item and to_week required: move a fixed-schedule item or discretionary bill to a later week; week 14 pushes it past the covenant test), 'sales_change' (pct required: flex forecast billings), 'stretch_ap' (days required: pay all suppliers N days later).",
        "input_schema": {
            "type": "object",
            "properties": {
                "scenario_type": {
                    "type": "string",
                    "enum": ["driver_sweep", "slip_collections", "accelerate_collection",
                             "defer_item", "sales_change", "stretch_ap"],
                },
                "customer": {"type": "string", "description": "Customer name, e.g. 'Vantage Aerospace'."},
                "days": {"type": "number", "description": "Days to slip, stretch, or pin to."},
                "pct": {"type": "number", "description": "Percent change to forecast billings, e.g. -10."},
                "item": {"type": "string", "description": "Substring matching a fixed-schedule item or vendor, e.g. 'capex deposit'."},
                "to_week": {"type": "integer", "description": "Destination week for defer_item (14 = past quarter end)."},
            },
            "required": ["scenario_type"],
        },
    },
    {
        "name": "compute_variance",
        "description": "Bridge the trailing 4 weeks of actual collections against the prior forecast. Attributes the miss between the flagged customer's slipped timing and all-other volume noise, with a weekly bridge table.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "draft_cash_narrative",
        "description": "Submit the structured treasury narrative for review. Sections must cover: (a) position and covenant summary, (b) the 13-week path and the trough, (c) what the probabilistic view adds and the breach risk, (d) recommended actions with their effect on covenant headroom. Each section carries a confidence level and open flags. Also submit the single recommended treasury action with its rationale and quantified effect.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                            "open_flags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Anything unresolved or that the reviewer should verify.",
                            },
                        },
                        "required": ["title", "content", "confidence"],
                    },
                },
                "recommended_action": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "The single recommended treasury action."},
                        "rationale": {"type": "string"},
                        "expected_headroom_effect": {"type": "number", "description": "Dollar change to week-13 covenant headroom."},
                        "expected_breach_prob_effect": {"type": "number", "description": "Change to breach probability, e.g. -0.12."},
                    },
                    "required": ["action", "rationale"],
                },
            },
            "required": ["sections", "recommended_action"],
        },
    },
    {
        "name": "submit_for_review",
        "description": "Route the narrative and recommended action to the human reviewer and pause the pipeline. Do not call any further tools until the review response arrives. This is a mandatory gate: the agent proposes, the human disposes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Brief message to the reviewer: what was found, what you recommend, where you are uncertain."},
            },
            "required": ["message"],
        },
    },
    {
        "name": "log_output",
        "description": "Write the complete audit trail after the reviewer's disposition: final narrative sections with reviewer actions, the disposition of the recommended action, and a one-paragraph summary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "final_sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "final_content": {"type": "string"},
                            "reviewer_action": {"type": "string", "enum": ["approved", "edited", "rejected"]},
                            "reviewer_notes": {"type": "string"},
                        },
                        "required": ["title", "final_content", "reviewer_action"],
                    },
                },
                "recommended_action_disposition": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "disposition": {"type": "string", "enum": ["approved", "edited", "rejected"]},
                        "notes": {"type": "string"},
                    },
                    "required": ["action", "disposition"],
                },
                "summary": {"type": "string", "description": "One-paragraph summary of the forecast, the risk, and the review outcome."},
            },
            "required": ["final_sections", "recommended_action_disposition", "summary"],
        },
    },
]
