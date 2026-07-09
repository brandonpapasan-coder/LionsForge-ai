from time import perf_counter

from app.schemas.market import HistoricalPriceRead, QuoteRead
from app.services.market_provider_health import ProviderHealthRegistry, provider_health_registry
from app.services.market_providers import MarketDataProvider


class MarketDataRoutingError(RuntimeError):
    pass


class MarketDataRouter:
    def __init__(
        self,
        providers: list[MarketDataProvider],
        health_registry: ProviderHealthRegistry | None = None,
    ) -> None:
        if not providers:
            raise ValueError("MarketDataRouter requires at least one provider")
        self.providers = providers
        self.health_registry = health_registry or provider_health_registry

    def _ordered_available_providers(self) -> list[MarketDataProvider]:
        available = [provider for provider in self.providers if self.health_registry.is_available(provider.name)]
        return available or self.providers

    def get_quote(self, symbol: str) -> QuoteRead:
        return self._execute(lambda provider: provider.get_quote(symbol))

    def get_historical_prices(self, symbol: str, limit: int = 30) -> list[HistoricalPriceRead]:
        return self._execute(lambda provider: provider.get_historical_prices(symbol, limit=limit))

    def _execute(self, operation):
        errors: list[str] = []
        for provider in self._ordered_available_providers():
            started_at = perf_counter()
            try:
                result = operation(provider)
            except Exception as exc:
                latency_ms = (perf_counter() - started_at) * 1000
                self.health_registry.record_failure(provider.name, exc, latency_ms=latency_ms)
                errors.append(f"{provider.name}: {exc}")
                continue
            latency_ms = (perf_counter() - started_at) * 1000
            self.health_registry.record_success(provider.name, latency_ms=latency_ms)
            return result
        raise MarketDataRoutingError("All market data providers failed: " + "; ".join(errors))
