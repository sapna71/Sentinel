from typing import AsyncGenerator
from app.graph.orchestrator import SentinelGraph
from app.streaming.manager import StreamingManager
from app.streaming.event_bus import EventBus
from app.schemas.streaming import StreamEventType
from app.resilience.provider_health import ProviderHealthManager

class ChatService:

    def __init__(
        self,
        streaming: StreamingManager,
        graph=None
    ) -> None:
        self.streaming = streaming
        self.graph = graph or SentinelGraph()

    async def process_request(
        self,
        trace_id,
        payload,
        event_bus: EventBus,
    ) -> AsyncGenerator:

        prompt = payload.get("prompt", "")

        # Check kill switch before doing anything
        if not await ProviderHealthManager.is_available():
            await self.streaming.emit(
                trace_id,
                StreamEventType.STATUS,
                {"message": "⛔ Primary model offline. Routing to fallback..."},
            )
        else:
            await self.streaming.emit(
                trace_id,
                StreamEventType.STATUS,
                {"message": "Analyzing request and selecting model..."},
            )

        try:
            # Pass kill switch state to graph so it knows to use fallback
            result = await self.graph.workflow.ainvoke({
                "prompt": prompt,
                "force_fallback": not await ProviderHealthManager.is_available(),
            })

            if result.get("is_fallback"):
                await self.streaming.emit(
                    trace_id,
                    StreamEventType.STATUS,
                    {"message": "Primary model offline. Serving response from fallback model..."},
                )

            await self.streaming.emit(
                trace_id,
                StreamEventType.TOKEN,
                {"token": result.get("response", "No response generated.")},
            )

            await self.streaming.emit(
                trace_id,
                StreamEventType.COMPLETION,
                {"status": "success", "provider": result.get("provider_used", "Unknown Provider")},
            )

        except Exception as e:
            await self.streaming.emit(
                trace_id,
                StreamEventType.ERROR,
                {"message": str(e)},
            )

        while True:
            yield await event_bus.consume()
    # ... rest of your existing stream logic