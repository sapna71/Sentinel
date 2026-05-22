from dataclasses import dataclass


@dataclass
class ProviderHealth:
    provider_name: str
    success_rate: float
    latency_ms: float
    circuit_state: str
    health_score: float