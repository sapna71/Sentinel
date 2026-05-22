import json

from schemas.streaming import StreamEvent


class SSEProtocol:

    @staticmethod
    def encode(event: StreamEvent) -> str:
        return (
            f"event: {event.type.value}\n"
            f"data: {json.dumps(event.model_dump(mode='json'))}\n\n"
        )