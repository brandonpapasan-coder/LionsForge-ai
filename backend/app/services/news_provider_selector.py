from app.core.config import get_settings
from app.services.news_providers import LiveNewsProvider, MockNewsProvider, NewsProvider


class NewsProviderConfigurationError(ValueError):
    pass


LIVE_NEWS_PROVIDER_NAMES = {"newsapi", "finnhub", "polygon", "alpha_vantage"}


def get_configured_news_provider() -> NewsProvider:
    settings = get_settings()
    provider_name = settings.news_provider.lower().strip()

    if provider_name == "mock":
        return MockNewsProvider()

    if provider_name in LIVE_NEWS_PROVIDER_NAMES:
        if not settings.news_api_key:
            raise NewsProviderConfigurationError(f"{provider_name} requires NEWS_API_KEY")
        return LiveNewsProvider(name=provider_name, api_key=settings.news_api_key)

    raise NewsProviderConfigurationError(f"Unsupported news provider: {provider_name}")
