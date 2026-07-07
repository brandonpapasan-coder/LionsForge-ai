# LionsForge AI

AI-powered investment research and trading platform.

## Current status

LionsForge AI is in early MVP development. The backend is being built as a FastAPI service with versioned APIs for research, market news, watchlists, portfolios, finance education, and future trading workflows.

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
POST /api/v1/research/analyze
GET  /api/v1/news/market
GET  /api/v1/watchlists?owner_id=1
POST /api/v1/watchlists?owner_id=1
GET  /api/v1/portfolios?owner_id=1
POST /api/v1/portfolios?owner_id=1
POST /api/v1/portfolios/{portfolio_id}/holdings?owner_id=1
```

## Backend foundation added

- FastAPI application with versioned routing
- Environment-driven settings
- SQLAlchemy database session setup
- SQLite default for local development
- User account model
- Account registration and login routes
- JWT access-token helper
- Persistent watchlist model and endpoints
- Persistent portfolio models and endpoints
- Mock research and market news API contracts

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
