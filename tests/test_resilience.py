import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

from app.core.config import settings
from app.graph.orchestrator import SentinelGraph
from app.schemas.streaming import StreamEventType
from app.streaming.event_bus import EventBus
from app.streaming.manager import StreamingManager
from app.services.chat_service import ChatService


class FakeProviderResponse:
    def __init__(self, success: bool, content: str | None = None, error: str | None = None):
        self.success = success
        self.content = content
        self.error = error
        self.latency = 0.0


def test_primary_failure_triggers_fallback_provider():
    graph = SentinelGraph()

    async def fake_call_model(model_name: str, prompt: str):
        if model_name == settings.PRIMARY_MODEL:
            return FakeProviderResponse(success=False, error="Primary LLM unavailable")

        return FakeProviderResponse(success=True, content="Fallback response from backup model")

    graph.provider_service.call_model = AsyncMock(side_effect=fake_call_model)

    initial_state = {
        "prompt": "Test prompt for resilience",
        "response": None,
        "error": None,
        "provider_used": None,
        "attempts": 0,
        "is_fallback": False,
        "tool_calls": [],
        "tool_outputs": [],
    }

    final_state = asyncio.run(graph.workflow.ainvoke(initial_state))

    assert final_state["provider_used"] == settings.FALLBACK_MODEL
    assert final_state["is_fallback"] is True
    assert final_state["response"] == "Fallback response from backup model"
    assert final_state.get("error") is None


def test_chat_service_streams_fallback_status_to_frontend():
    bus = EventBus()
    streaming = StreamingManager(bus)
    service = ChatService(streaming=streaming)

    service.graph.workflow.ainvoke = AsyncMock(return_value={
        "response": "Fallback response from backup model",
        "provider_used": settings.FALLBACK_MODEL,
        "is_fallback": True,
    })

    async def collect_events():
        events = []
        async for event in service.process_request(trace_id=uuid4(), payload={"prompt": "Test prompt"}, event_bus=bus):
            events.append(event)
            if event.type in {StreamEventType.COMPLETION, StreamEventType.ERROR}:
                break
        return events

    events = asyncio.run(collect_events())

    assert any(
        event.type == StreamEventType.STATUS and "Fail-over" in event.payload.get("message", "")
        for event in events
    )
    assert any(event.type == StreamEventType.COMPLETION for event in events)
