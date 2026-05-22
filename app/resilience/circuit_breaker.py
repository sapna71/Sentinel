from enum import Enum
from datetime import datetime, timedelta


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.failures = 0
        self.last_failure_time: datetime | None = None
        self.state = CircuitState.CLOSED

    async def allow_request(self) -> bool:

        if self.state == CircuitState.OPEN:

            if (
                self.last_failure_time
                and datetime.utcnow() - self.last_failure_time
                > timedelta(seconds=self.recovery_timeout)
            ):
                self.state = CircuitState.HALF_OPEN
                return True

            return False

        return True

    async def record_success(self) -> None:
        self.failures = 0
        self.state = CircuitState.CLOSED

    async def record_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = datetime.utcnow()

        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN