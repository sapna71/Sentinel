from enum import Enum
from typing import Any
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field


class StreamEventType(str, Enum):
    TOKEN = "token"
    PROVIDER_SWITCH = "provider_switch"
    TOOL_EXECUTION = "tool_execution"
    FALLBACK_TRIGGERED = "fallback_triggered"
    STATUS = "status"
    COMPLETION = "completion"
    ERROR = "error"


class StreamEvent(BaseModel):
    event_id: UUID
    trace_id: UUID
    type: StreamEventType
    timestamp: datetime
    payload: dict[str, Any] = Field(default_factory=dict)