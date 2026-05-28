from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.services.chat_service import ChatService
from app.streaming.protocol import SSEProtocol
from app.streaming.event_bus import EventBus
from app.streaming.manager import StreamingManager
from app.schemas.streaming import StreamEventType
from app.resilience.provider_health import ProviderHealthManager
from uuid import uuid4
from app.graph.orchestrator import SentinelGraph
_graph_instance = SentinelGraph()


router = APIRouter()  # ← only ONE router

async def get_chat_service():
    bus = EventBus()
    manager = StreamingManager(bus)
    return ChatService(streaming=manager, graph=_graph_instance)

@router.post("/stream")
async def stream_chat(
    payload: dict,
    service: ChatService = Depends(get_chat_service),
):
    trace_id = uuid4()

    async def event_generator():
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

# Kill switch routes — no prefix here, main.py prefix handles it
@router.post("/provider/kill")
async def kill_provider():
    await ProviderHealthManager.force_kill()
    return {"status": "killed", "message": "Primary provider marked as unavailable"}

@router.post("/provider/restore")
async def restore_provider():
    await ProviderHealthManager.force_restore()
    return {"status": "restored", "message": "Primary provider restored"}

@router.get("/provider/status")
async def provider_status():
    status = await ProviderHealthManager.get_status()
    return status

@router.post("/provider/chaos/trip")
async def trip_circuit_breaker():
    cb = _graph_instance.primary_cb
    # record failures up to threshold to force OPEN state
    for _ in range(cb.failure_threshold):
        await cb.record_failure()
    return {
        "status": "tripped",
        "state": cb.state.value,
        "failures": cb.failures,
        "message": f"Circuit breaker tripped after {cb.failure_threshold} forced failures"
    }

@router.post("/provider/chaos/reset")
async def reset_circuit_breaker():
    await _graph_instance.primary_cb.record_success()
    return {
        "status": "reset",
        "state": _graph_instance.primary_cb.state.value,
        "message": "Circuit breaker reset to CLOSED"
    }
@router.get("/provider/chaos/state")
async def circuit_breaker_state():
    cb = _graph_instance.primary_cb
    return {
        "state": cb.state.value,
        "failures": cb.failures,
        "threshold": cb.failure_threshold,
        "recovery_timeout": cb.recovery_timeout,
        "last_failure": cb.last_failure_time.isoformat() if cb.last_failure_time else None,
    }