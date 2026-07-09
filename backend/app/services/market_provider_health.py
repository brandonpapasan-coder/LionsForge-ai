from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ProviderHealth:
    name: str
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    last_latency_ms: float | None = None
    last_error: str | None = None
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None

    @property
    def total_count(self) -> int:
        return self.success_count + self.failure_count

    @property
    def error_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.failure_count / self.total_count

    def is_available(self, failure_threshold: int) -> bool:
        return self.consecutive_failures < failure_threshold


@dataclass
class ProviderHealthRegistry:
    failure_threshold: int = 3
    _health: dict[str, ProviderHealth] = field(default_factory=dict)

    def get(self, provider_name: str) -> ProviderHealth:
        if provider_name not in self._health:
            self._health[provider_name] = ProviderHealth(name=provider_name)
        return self._health[provider_name]

    def record_success(self, provider_name: str, latency_ms: float) -> None:
        health = self.get(provider_name)
        health.success_count += 1
        health.consecutive_failures = 0
        health.last_latency_ms = latency_ms
        health.last_error = None
        health.last_success_at = datetime.now(timezone.utc)

    def record_failure(self, provider_name: str, error: Exception, latency_ms: float | None = None) -> None:
        health = self.get(provider_name)
        health.failure_count += 1
        health.consecutive_failures += 1
        health.last_latency_ms = latency_ms
        health.last_error = str(error)
        health.last_failure_at = datetime.now(timezone.utc)

    def is_available(self, provider_name: str) -> bool:
        return self.get(provider_name).is_available(self.failure_threshold)

    def snapshot(self) -> dict[str, ProviderHealth]:
        return dict(self._health)

    def reset(self) -> None:
        self._health.clear()


provider_health_registry = ProviderHealthRegistry()
