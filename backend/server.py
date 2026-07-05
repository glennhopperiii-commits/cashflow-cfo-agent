"""FastAPI + WebSocket wrapper around the Phase 1 harness.

This file adds transport, not logic. It imports the exact tool functions and
agent loop from cashflow_harness and supplies the WebSocket implementation of
the human-gate callback. The event protocol is the HFMA protocol, verbatim:
step_started, step_completed, agent_text, review_requested, pipeline_complete
(plus report_generated); the frontend sends review_submitted.

Run from the project root:  uvicorn backend.server:app --port 8000
"""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from cashflow_harness.agent import run_agent
from cashflow_harness.config import OUTPUT_DIR
from cashflow_harness.logger import AuditLogger

from .models import PipelineStatus

# Demo pacing multiplier for cashflow_harness.agent.DEMO_DELAYS.
PACE = 1.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pipeline_status = PipelineStatus.IDLE
    app.state.active_ws = None
    app.state.review_event = asyncio.Event()
    app.state.review_response = None
    app.state.audit_logger = AuditLogger()
    app.state.agent_task = None
    yield


app = FastAPI(title="Cascade Precision Cash Flow Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _accept_review(data: dict) -> None:
    app.state.review_response = {
        "decisions": data.get("decisions", []),
        "recommended_action_disposition": data.get("recommended_action_disposition", {}),
    }
    app.state.review_event.set()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    app.state.active_ws = ws
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            if msg.get("event") == "review_submitted":
                _accept_review(msg.get("data", {}))
    except WebSocketDisconnect:
        if app.state.active_ws is ws:
            app.state.active_ws = None


async def _ws_callback(event: str, data: dict) -> None:
    ws = app.state.active_ws
    if ws is None:
        return
    await ws.send_json({
        "event": event,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def _ws_review_handler(payload: dict) -> dict:
    """The WebSocket implementation of the human gate.

    review_requested has already been emitted by the agent loop; block here
    until the frontend answers (over WS or POST /api/review). This is what
    makes the gate real: the agent task is parked on this await.
    """
    app.state.pipeline_status = PipelineStatus.REVIEW
    app.state.review_event.clear()
    app.state.review_response = None
    await app.state.review_event.wait()
    app.state.pipeline_status = PipelineStatus.RUNNING
    return app.state.review_response or {
        "decisions": [],
        "recommended_action_disposition": {},
    }


@app.post("/api/run")
async def start_pipeline():
    if app.state.pipeline_status in (PipelineStatus.RUNNING, PipelineStatus.REVIEW):
        return {"status": "already_running"}

    app.state.pipeline_status = PipelineStatus.RUNNING
    app.state.review_event.clear()
    app.state.review_response = None
    app.state.audit_logger = AuditLogger()

    async def _run():
        try:
            await _ws_callback("pipeline_started", {})
            await run_agent(
                ws_callback=_ws_callback,
                review_handler=_ws_review_handler,
                audit_logger=app.state.audit_logger,
                pace=PACE,
            )
            app.state.pipeline_status = PipelineStatus.COMPLETE
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            app.state.pipeline_status = PipelineStatus.ERROR
            await _ws_callback("pipeline_error", {"error": str(e)})

    app.state.agent_task = asyncio.create_task(_run())
    return {"status": "started"}


@app.post("/api/review")
async def submit_review(payload: dict):
    _accept_review(payload)
    return {"status": "review_submitted"}


@app.post("/api/reset")
async def reset_pipeline():
    if app.state.agent_task and not app.state.agent_task.done():
        app.state.agent_task.cancel()
        try:
            await app.state.agent_task
        except asyncio.CancelledError:
            pass

    app.state.pipeline_status = PipelineStatus.IDLE
    app.state.review_event.clear()
    app.state.review_response = None
    app.state.audit_logger = AuditLogger()

    await _ws_callback("pipeline_reset", {})
    return {"status": "reset"}


@app.get("/api/replay")
async def get_replay():
    replay_path = OUTPUT_DIR / "replay_capture.json"
    if not replay_path.exists():
        return {"events": [], "error": "No replay capture found. Run the pipeline first."}
    with open(replay_path) as f:
        return json.load(f)


@app.get("/api/report")
async def get_report():
    report_path = OUTPUT_DIR / "cashflow_13wk.xlsx"
    if not report_path.exists():
        return {"error": "No workbook found. Run the pipeline first."}
    return FileResponse(
        report_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="cascade-precision-13-week-cashflow.xlsx",
    )


@app.get("/api/status")
async def get_status():
    return {"status": app.state.pipeline_status.value}


@app.get("/api/events")
async def get_events():
    return {"events": app.state.audit_logger.events}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
