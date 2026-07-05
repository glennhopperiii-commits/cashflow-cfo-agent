import json
from datetime import datetime, timezone

from .config import OUTPUT_DIR


class AuditLogger:
    """Append-only audit trail. Every pipeline event lands here with a
    timestamp; write() persists the trail and write_replay() persists the
    same sequence for the Phase 2 replay safety net."""

    def __init__(self):
        self.events: list[dict] = []

    def log(self, event_type: str, data: dict) -> None:
        self.events.append({
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def write(self) -> str:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / "audit_log.json"
        with open(path, "w") as f:
            json.dump({"events": self.events, "event_count": len(self.events)}, f, indent=2)
        return str(path)

    def write_replay(self) -> str:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / "replay_capture.json"
        with open(path, "w") as f:
            json.dump({"events": self.events}, f, indent=2)
        return str(path)
