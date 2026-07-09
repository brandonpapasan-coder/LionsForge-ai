# Market Data Providers

The backend now routes market quotes through a provider abstraction and selector.

## Current provider

- `mock`: deterministic placeholder quote data for local development and tests.

## Configuration

```bash
MARKET_DATA_PROVIDER=mock
MARKET_DATA_API_KEY=
```

## Provider selector

Provider selection lives in `app/services/provider_selector.py`.

Current behavior:

- `mock` returns the mock market data provider.
- `alpaca`, `polygon`, `finnhub`, and `twelve_data` are recognized live-provider names.
- Live-provider names require `MARKET_DATA_API_KEY`.
- Live providers currently use a scaffold until provider-specific HTTP clients are implemented.
- Unsupported provider names raise a configuration error.

## Quote cache

Quote requests pass through an in-memory cache in `app/services/quote_cache.py`.

Current behavior:

- Single-symbol requests reuse cached values within the cache window.
- Batch quote requests normalize and deduplicate symbols.
- The cache can be replaced later with Redis or another shared cache.

## Next provider work

A live provider can be completed by implementing the provider interface in `app/services/market_providers.py` and registering provider-specific HTTP behavior in the selector.
