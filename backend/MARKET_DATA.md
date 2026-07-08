# Market Data Providers

The backend now routes market quotes through a provider abstraction.

## Current provider

- `mock`: deterministic placeholder quote data for local development and tests.

## Configuration

```bash
MARKET_DATA_PROVIDER=mock
MARKET_DATA_API_KEY=
```

## Next provider work

A live provider can be added by implementing the provider interface in `app/services/market_providers.py` and updating the selector in `app/services/market_data_service.py`.

Planned live provider options:

- Alpaca
- Polygon
- Finnhub
- Twelve Data
