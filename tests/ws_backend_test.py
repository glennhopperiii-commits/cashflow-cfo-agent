"""End-to-end WebSocket test of the Phase 2 backend.

Costs one live agent run (needs ANTHROPIC_API_KEY in .env and the backend up:
`python3 -m uvicorn backend.server:app --port 8000`). Connects to the event
stream, answers the review gate (all approvals), and verifies the protocol.

Close other browser tabs pointed at the app first, or run with them open to
exercise the multi-client broadcast: every connected client receives every
event, and any client may answer the gate.

Run from the repo root:  python3 tests/ws_backend_test.py
"""

import asyncio
import json
import sys
import urllib.request

import websockets

BASE = "http://localhost:8000"


def post(path, payload=None):
    req = urllib.request.Request(
        BASE + path, method="POST",
        data=json.dumps(payload or {}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


async def main():
    seen = []
    async with websockets.connect("ws://localhost:8000/ws") as ws:
        print("run:", post("/api/run"), flush=True)

        async for raw in ws:
            msg = json.loads(raw)
            event, data = msg["event"], msg["data"]
            seen.append(event)

            if event == "step_started":
                print(f">> {data['step']}", flush=True)
            elif event == "step_completed" and data["step"] == "build_deterministic_forecast":
                out = data["output"]
                print(f"   trough ${out['trough_cash']:,.0f} wk {out['trough_week']} | "
                      f"headroom ${out['covenant_headroom']:,.0f}", flush=True)
            elif event == "step_completed" and data["step"] == "run_monte_carlo":
                print(f"   P(breach) {data['output']['p_covenant_breach']:.1%}", flush=True)
            elif event == "review_requested":
                sections = data["sections"]
                ra = data["recommended_action"]
                print(f"REVIEW GATE: {len(sections)} sections", flush=True)
                await asyncio.sleep(1)
                await ws.send(json.dumps({
                    "event": "review_submitted",
                    "data": {
                        "decisions": [
                            {"section_title": s["title"], "action": "approved",
                             "edited_content": None, "notes": ""}
                            for s in sections
                        ],
                        "recommended_action_disposition": {
                            "action": ra.get("action", ""),
                            "disposition": "approved",
                            "notes": "Approved via test client",
                        },
                    },
                }))
                print("   review submitted over WS", flush=True)
            elif event == "report_generated":
                print(f"REPORT: {data['path']}", flush=True)
                break
            elif event == "pipeline_error":
                print("PIPELINE ERROR:", data, flush=True)
                return 1

    required = {"pipeline_started", "step_started", "step_completed",
                "review_requested", "pipeline_complete", "report_generated"}
    missing = required - set(seen)
    print(f"\nevents seen: {len(seen)} | protocol check:",
          "PASS" if not missing else f"MISSING {missing}", flush=True)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
