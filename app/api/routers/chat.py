from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.services.chat_service import ChatService
from app.streaming.protocol import SSEProtocol
from app.streaming.event_bus import EventBus
from app.streaming.manager import StreamingManager
from app.schemas.streaming import StreamEventType
from uuid import uuid4

router = APIRouter()

# Dependency to provide ChatService with a StreamingManager
async def get_chat_service():
    bus = EventBus()
    manager = StreamingManager(bus)
    return ChatService(streaming=manager)

@router.post("/stream")
async def stream_chat(
    payload: dict,
    service: ChatService = Depends(get_chat_service),
):
    trace_id = uuid4()
    
    async def event_generator():
        # We need the bus that was created in the dependency
        # Since ChatService doesn't expose the bus, we recreate it or pass it.
        # For this architecture, we'll use the bus associated with the manager.
        bus = service.streaming.bus
        
        orchestration_task = service.process_request(
            trace_id=trace_id,
            payload=payload,
            event_bus=bus,
        )

        async for event in orchestration_task:
            yield SSEProtocol.encode(event)

            if event.type in {StreamEventType.COMPLETION, StreamEventType.ERROR}:
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )