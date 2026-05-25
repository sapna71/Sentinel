from typing import AsyncGenerator
from app.graph.orchestrator import SentinelGraph
from app.streaming.manager import StreamingManager
from app.streaming.event_bus import EventBus
from app.schemas.streaming import StreamEventType

class ChatService:

    def __init__(
        self,
        streaming: StreamingManager,
    ) -> None:
        self.streaming = streaming
        self.graph = SentinelGraph()

    async def process_request(
        self,
        trace_id,
        payload,
        event_bus: EventBus,
    ) -> AsyncGenerator:

        prompt = payload.get("prompt", "")
        
        await self.streaming.emit(
            trace_id,
            StreamEventType.STATUS,
            {"message": "Analyzing request and selecting model..."},
        )

        # We run the graph and capture the result
        # In a full implementation, we would wrap the graph nodes to emit events
        # For the vertical slice, we emit the key transitions.
        
        try:
            result = await self.graph.workflow.ainvoke({"prompt": prompt})
            
            if result.get("is_fallback"):
                await self.streaming.emit(
                    trace_id,
                    StreamEventType.STATUS,
                    {"message": "Primary model unstable. Fail-over triggered to backup system..."},
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