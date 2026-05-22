from uuid import uuid4
from datetime import datetime

from streaming.event_bus import EventBus
from schemas.streaming import (
    StreamEvent,
    StreamEventType,
)


class StreamingManager:

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus

    async def emit(
        self,
        trace_id,
        event_type: StreamEventType,
        payload: dict,
    ) -> None:

        event = StreamEvent(
            event_id=uuid4(),
            trace_id=trace_id,
            type=event_type,
            timestamp=datetime.utcnow(),
            payload=payload,
        )

        await self.bus.publish(event)