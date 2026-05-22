from schemas.streaming import StreamEventType
from streaming.manager import StreamingManager


class ChatService:

    def __init__(
        self,
        streaming: StreamingManager,
    ) -> None:
        self.streaming = streaming

    async def process_request(
        self,
        trace_id,
        payload,
        event_bus,
    ):

        await self.streaming.emit(
            trace_id,
            StreamEventType.STATUS,
            {"message": "starting_orchestration"},
        )

        for token in ["Hello", " ", "world"]:

            await self.streaming.emit(
                trace_id,
                StreamEventType.TOKEN,
                {"token": token},
            )

        await self.streaming.emit(
            trace_id,
            StreamEventType.COMPLETION,
            {"status": "success"},
        )

        while True:
            yield await event_bus.consume()