from dataclasses import dataclass

from app.core.config import Settings
from app.services.market_provider_health import ProviderHealthRegistry


@dataclass(frozen=True)
class MarketDependencyReadiness:
    status: str
    primary_provider: str
    unavailable_providers: tuple[str, ...]


def configured_provider_names(settings: Settings) -> list[str]:
    raw_names = [
        settings.market_data_provider,
        *settings.market_data_failover_providers.split(","),
    ]
    names: list[str] = []
    for raw_name in raw_names:
        name = raw_name.strip().lower()
        if name and name not in names:
            names.append(name)
    return names or ["mock"]


def evaluate_market_dependencies(
    settings: Settings,
    health_registry: ProviderHealthRegistry,
) -> MarketDependencyReadiness:
    provider_names = configured_provider_names(settings)
    primary_provider = provider_names[0]
    unavailable = tuple(
        name for name in provider_names if not health_registry.is_available(name)
    )

    if primary_provider in unavailable:
        status = "unavailable"
    elif unavailable:
        status = "degraded"
    else:
        status = "available"

    return MarketDependencyReadiness(
        status=status,
        primary_provider=primary_provider,
        unavailable_providers=unavailable,
    )
