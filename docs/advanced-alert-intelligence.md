# Advanced Alert Intelligence

LionsForge AI exposes authenticated event-alert delivery through:

`POST /api/v1/advanced-alerts/events`

Supported categories:

- `earnings`
- `sec_filing`
- `analyst_change`
- `macro_event`
- `portfolio_risk`

Every accepted event is persisted as an in-app alert notification and is visible through the existing notifications endpoint. Symbols are normalized to uppercase. Event identifiers are deterministic for the user, category, symbol, headline, event time, and portfolio context.

Portfolio-risk events require `portfolio_id`, `risk_score`, and `threshold`. The risk score must meet or exceed the configured threshold, preventing below-threshold events from creating critical notifications.

The endpoint does not fetch live market or filing data. Callers must supply verified event context. Existing automation rules continue to provide scheduled portfolio-review and watchlist-digest notifications.
