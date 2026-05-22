import asyncio

from schemas.streaming import StreamEvent


class EventBus:

    def __init__(self) -> None:
        self._queue: asyncio.Queue[StreamEvent] = asyncio.Queue()

    async def publish(self, event: StreamEvent) -> None:
        await self._queue.put(event)

    async def consume(self) -> StreamEvent:
        return await self._queue.get()