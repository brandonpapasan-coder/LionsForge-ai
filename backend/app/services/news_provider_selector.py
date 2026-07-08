from app.core.config import get_settings
from app.services.news_providers import MockNewsProvider, NewsProvider


class NewsProviderConfigurationError(ValueError):
    pass


SUPPORTED_NEWS_PROVIDERS = {"mock"}


def get_configured_news_provider() -> NewsProvider:
    settings = get_settings()
    provider_name = settings.news_provider.lower().strip()

    if provider_name == "mock":
        return MockNewsProvider()

    raise NewsProviderConfigurationError(f"Unsupported news provider: {provider_name}")
