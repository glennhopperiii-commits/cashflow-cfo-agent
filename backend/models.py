from enum import Enum


class PipelineStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    REVIEW = "review"
    COMPLETE = "complete"
    ERROR = "error"
