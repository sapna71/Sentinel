from dataclasses import dataclass


@dataclass
class ProviderHealth:
    provider_name: str
    success_rate: float
    latency_ms: float
    circuit_state: str
    health_score: float

import asyncio
from datetime import datetime

class ProviderHealthManager:
    _killed: bool = False
    _killed_at: datetime | None = None

    @classmethod
    async def force_kill(cls):
        cls._killed = True
        cls._killed_at = datetime.utcnow()

    @classmethod
    async def force_restore(cls):
        cls._killed = False
        cls._killed_at = None

    @classmethod
    async def is_available(cls) -> bool:
        return not cls._killed

    @classmethod
    async def get_status(cls) -> dict:
        return {
            "provider": "gemma4-cloud",
            "available": not cls._killed,
            "killed_at": cls._killed_at.isoformat() if cls._killed_at else None,
        }