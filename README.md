# LionsForge AI

AI-powered investment research and trading platform.

## Current status

LionsForge AI is in early MVP development. The backend is being built as a FastAPI service with versioned APIs for research, market news, watchlists, finance education, and future trading/risk workflows.

## Backend quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m app.db.init_db
uvicorn app.main:app --reload
```

Open the API docs at:

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
GET  /api/v1/watchlists
POST /api/v1/watchlists
```

## Backend foundation added

- FastAPI application with versioned routing
- Environment-driven settings
- SQLAlchemy database session setup
- SQLite default for local development
- User database model
- Account registration and login routes
- Secret hashing and JWT access-token helper
- Mock research, news, and watchlist API contracts

## MVP roadmap

1. Backend API foundation
2. User authentication and accounts
3. Database models for users, watchlists, portfolios, and alerts
4. Market data provider integration
5. News, filings, and documented business deal ingestion
6. AI research summary engine
7. Risk scoring and portfolio monitoring
8. Trading simulation and broker integration
9. Web dashboard
10. Mobile-ready API support

## Compliance note

LionsForge AI is intended to support research and education workflows. It should not present mock or model-generated content as financial advice. Live trading features must include risk controls, audit logs, user disclosures, and regulatory review before production use.
