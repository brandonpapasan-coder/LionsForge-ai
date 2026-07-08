# News Providers

Company news routes use a provider abstraction.

## Current provider

- `mock`: local placeholder company news for development and tests.

## Configuration

```bash
NEWS_PROVIDER=mock
NEWS_API_KEY=
```

## Recognized live provider names

- `newsapi`
- `finnhub`
- `polygon`
- `alpha_vantage`

Live provider names require `NEWS_API_KEY`. Provider-specific HTTP clients are scaffolded for future implementation.
