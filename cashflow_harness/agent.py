"""Agent orchestration loop: the Anthropic tool-use pattern.

The human review gate is a callback. Phase 1 (the notebook) passes a handler
that prompts in a cell; Phase 2 (the server) passes one that emits
review_requested over the WebSocket and blocks on the frontend's response.
With no handler, every section auto-approves (CLI mode).

Event protocol (kept verbatim from the HFMA build so the Phase 2 frontend
can be cloned): step_started, step_completed, agent_text, review_requested,
pipeline_complete. The frontend sends review_submitted.
"""

import asyncio
import json
from typing import Any, Awaitable, Callable, Optional

import anthropic

from .config import ANTHROPIC_API_KEY, INITIAL_PROMPT, MAX_TOKENS, MODEL, SYSTEM_PROMPT
from .logger import AuditLogger
from .tool_schemas import TOOLS
from .tools import execute_tool

WsCallback = Callable[[str, dict], Awaitable[None]]
ReviewHandler = Callable[[dict], Awaitable[dict]]

# Demo pacing: seconds to pause before each tool executes, scaled by the
# `pace` argument (0 in notebook/CLI, 1.0 for the recorded demo UI).
DEMO_DELAYS = {
    "load_facility_and_position": 3.0,
    "load_receivables": 3.5,
    "load_payables_and_fixed": 3.5,
    "build_deterministic_forecast": 4.0,
    "run_monte_carlo": 4.0,
    "run_scenario": 3.0,
    "compute_variance": 3.0,
    "draft_cash_narrative": 4.0,
    "submit_for_review": 1.0,
    "log_output": 1.5,
}


async def _noop_callback(event: str, data: dict) -> None:
    pass


async def run_agent(
    ws_callback: WsCallback = _noop_callback,
    review_handler: Optional[ReviewHandler] = None,
    audit_logger: Optional[AuditLogger] = None,
    pace: float = 0.0,
) -> dict:
    # Fall back to the live environment: notebooks often set the key after
    # this module was first imported.
    import os
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY"))
    logger = audit_logger or AuditLogger()
    messages: list[dict] = [{"role": "user", "content": INITIAL_PROMPT}]
    pipeline_state: dict[str, Any] = {}

    logger.log("pipeline_started", {"prompt": INITIAL_PROMPT})

    while True:
        response = await client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        tool_results = []
        for block in response.content:
            if block.type == "text":
                await ws_callback("agent_text", {"text": block.text})
                logger.log("agent_text", {"text": block.text})

            elif block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input

                delay = DEMO_DELAYS.get(tool_name, 0) * pace
                if delay > 0:
                    await asyncio.sleep(delay)

                await ws_callback("step_started", {"step": tool_name, "input": tool_input})
                logger.log("step_started", {"step": tool_name, "input": tool_input})

                if tool_name == "submit_for_review":
                    result = await _handle_review_gate(
                        tool_input, ws_callback, review_handler, pipeline_state, logger
                    )
                else:
                    result = execute_tool(tool_name, tool_input)

                _capture_state(pipeline_state, tool_name, tool_input, result)

                await ws_callback("step_completed", {"step": tool_name, "output": result})
                logger.log("step_completed", {"step": tool_name, "output": result})

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

        messages.append({"role": "assistant", "content": _serialize_content(response.content)})
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        if response.stop_reason == "end_turn":
            logger.log("pipeline_complete", {})
            await ws_callback("pipeline_complete", {})
            break

    # The sponsor deliverable: a traditional 13-week cash flow workbook built
    # from the same engine the agent used. Never let a report failure break
    # the pipeline run.
    try:
        from .report import write_xlsx
        workbook_path = write_xlsx()
        pipeline_state["workbook_path"] = workbook_path
        logger.log("report_generated", {"path": workbook_path})
        await ws_callback("report_generated", {"path": workbook_path})
    except Exception as exc:  # noqa: BLE001
        logger.log("report_failed", {"error": str(exc)})

    logger.write()
    logger.write_replay()
    return {"status": "complete", "state": pipeline_state}


def _capture_state(state: dict, tool_name: str, tool_input: dict, result: dict) -> None:
    """Keep the pieces later steps and the Phase 2 UI need."""
    if tool_name == "build_deterministic_forecast":
        state["deterministic"] = result
    elif tool_name == "run_monte_carlo":
        state["monte_carlo"] = result
    elif tool_name == "run_scenario":
        state.setdefault("scenarios", []).append({"input": tool_input, "output": result})
    elif tool_name == "compute_variance":
        state["variance"] = result
    elif tool_name == "draft_cash_narrative" and "error" not in result:
        state["narrative_sections"] = tool_input.get("sections", [])
        state["recommended_action"] = tool_input.get("recommended_action", {})
    elif tool_name == "log_output":
        state["final_sections"] = tool_input.get("final_sections", [])
        state["recommended_action_disposition"] = tool_input.get("recommended_action_disposition", {})
        state["report_summary"] = tool_input.get("summary", "")


async def _handle_review_gate(
    tool_input: dict,
    ws_callback: WsCallback,
    review_handler: Optional[ReviewHandler],
    pipeline_state: dict,
    logger: AuditLogger,
) -> dict:
    payload = {
        "sections": pipeline_state.get("narrative_sections", []),
        "recommended_action": pipeline_state.get("recommended_action", {}),
        "message": tool_input.get("message", ""),
    }
    await ws_callback("review_requested", payload)
    logger.log("review_requested", payload)

    if review_handler is not None:
        review = await review_handler(payload)
    else:
        review = {
            "decisions": [
                {"section_title": s.get("title", ""), "action": "approved",
                 "edited_content": None, "notes": "Auto-approved (no review handler)."}
                for s in payload["sections"]
            ],
            "recommended_action_disposition": {
                "action": payload["recommended_action"].get("action", ""),
                "disposition": "approved",
                "notes": "Auto-approved (no review handler).",
            },
        }

    pipeline_state["review"] = review
    logger.log("review_completed", review)
    return {"status": "review_complete", **review}


def _serialize_content(content) -> list[dict]:
    serialized = []
    for block in content:
        if block.type == "text":
            serialized.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            serialized.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
    return serialized


async def _cli_callback(event: str, data: dict) -> None:
    if event == "agent_text":
        print(f"\n[Agent] {data['text']}")
    elif event == "step_started":
        print(f"\n>>> {data['step']}  input={json.dumps(data['input'])[:160]}")
    elif event == "step_completed":
        out = json.dumps(data["output"])
        print(f"    done ({len(out)} bytes): {out[:220]}")
    elif event == "review_requested":
        print(f"\n{'=' * 60}\nREVIEW GATE  ({len(data.get('sections', []))} sections)")
        print(f"Recommended action: {data.get('recommended_action', {}).get('action', '')}")
        print("=" * 60)
    elif event == "pipeline_complete":
        print(f"\n{'=' * 60}\nPIPELINE COMPLETE\n{'=' * 60}")


if __name__ == "__main__":
    print("Cascade Precision Cash Flow Agent -- CLI mode (auto-approve)")
    result = asyncio.run(run_agent(ws_callback=_cli_callback))
    print(f"\nFinal status: {result['status']}")
