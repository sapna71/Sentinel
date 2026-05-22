from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from services.chat_service import ChatService
from streaming.protocol import SSEProtocol
from streaming.event_bus import EventBus

router = APIRouter()


@router.post("/chat/stream")
async def stream_chat(
    payload: dict,
    service: ChatService = Depends(),
):

    trace_id = uuid4()

    async def event_generator():

        bus = EventBus()

        orchestration_task = service.process_request(
            trace_id=trace_id,
            payload=payload,
            event_bus=bus,
        )

        async for event in orchestration_task:
            yield SSEProtocol.encode(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )