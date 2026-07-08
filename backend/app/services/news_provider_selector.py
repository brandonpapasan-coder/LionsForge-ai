from app.services.news_providers import MockNewsProvider, NewsProvider


class NewsProviderConfigurationError(ValueError):
    pass


def get_configured_news_provider() -> NewsProvider:
    return MockNewsProvider()
