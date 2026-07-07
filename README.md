# LionsForge AI

AI-powered investment research and trading platform.

## Current status

LionsForge AI is in early MVP development. The backend uses FastAPI with versioned APIs for research, market data, news, watchlists, portfolios, alerts, education, and future trading workflows.

## Backend quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.db.init_db
uvicorn app.main:app --reload
```

API docs:

```text
http://127.0.0.1:8000/docs
```

## Available endpoints

```text
GET  /
GET  /health
GET  /ready
GET  /platform
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
POST /api/v1/research/analyze
GET  /api/v1/market/quotes/{symbol}
POST /api/v1/market/quotes
GET  /api/v1/news/market
GET  /api/v1/watchlists
POST /api/v1/watchlists
GET  /api/v1/portfolios
POST /api/v1/portfolios
POST /api/v1/portfolios/{portfolio_id}/holdings
GET  /api/v1/alerts
POST /api/v1/alerts
GET  /api/v1/alerts/evaluate
```

Authenticated routes use bearer tokens from `/api/v1/auth/login`.

## Backend foundation added

- FastAPI application with versioned routing
- Environment-driven settings
- SQLAlchemy database session setup
- SQLite local database default
- User account model and auth routes
- Authenticated profile endpoint
- Protected watchlist routes
- Protected portfolio routes
- Protected alert routes
- Mock market quote service and endpoints
- Research response with quote context
- Persistent watchlist model and endpoints
- Persistent portfolio models and endpoints
- Persistent alert model and evaluation endpoint
- Mock news API contract

## MVP roadmap

1. Backend API foundation
2. User accounts
3. Database models for saved lists, portfolios, and alerts
4. Market data provider integration
5. News and filing ingestion
6. AI research summary engine
7. Portfolio monitoring
8. Trading simulation and broker integration
9. Web dashboard
10. Mobile-ready API support

## Compliance note

LionsForge AI is intended to support research and education workflows. Live trading features must include risk controls, audit logs, user disclosures, and regulatory review before production use.
