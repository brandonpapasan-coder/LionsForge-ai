# LionsForge AI

LionsForge AI is an AI-assisted research, evidence validation, knowledge management, and education platform. It is designed to help people investigate complex questions, organize supporting material, expose uncertainty, preserve research history, and strengthen research skills while keeping humans responsible for conclusions and approvals.

## Current status

The repository is under active MVP development. The current application includes a FastAPI backend, a Next.js frontend, authenticated research workflows, institutional knowledge-quality views, automated backend and frontend testing, deployment validation, and security checks.

The repository also contains legacy investment-research modules from an earlier product direction. Those modules are not the strategic focus of LionsForge AI and should be treated as compatibility or migration candidates until they are explicitly retained, reframed, or removed.

## Product principles

- Evidence and provenance should remain visible.
- AI output should distinguish evidence, inference, assumptions, and uncertainty.
- Significant research conclusions remain subject to human review.
- Knowledge changes should be traceable through history and audit records.
- Education should be integrated with practical research workflows.
- Security, accessibility, reliability, and maintainability are release requirements.

## Repository structure

```text
backend/     FastAPI application, data models, services, and backend tests
frontend/    Next.js application, API proxies, components, and Vitest tests
infra/       Deployment and infrastructure definitions when present
docs/        Engineering, testing, and operational documentation
```

## Backend quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.db.init_db
python scripts/smoke_backend.py
uvicorn app.main:app --reload
```

If local SQLite state is stale, reset it:

```bash
rm -f lionsforge.db test_lionsforge.db ci_lionsforge.db
python -m app.db.init_db
python scripts/smoke_backend.py
```

API documentation is available locally at:

```text
http://127.0.0.1:8000/docs
```

## Frontend quick start

```bash
cd frontend
npm ci
npm run dev
```

Common validation commands:

```bash
npm test
npx tsc --noEmit
npm run build
```

## Active platform capabilities

Current development is centered on:

- User authentication and protected application routes
- Research projects and project-scoped workflows
- Evidence and institutional knowledge records
- Knowledge-quality metrics, risks, priorities, and recent activity
- Project-level quality drill-down with safe inaccessible-project handling
- Transparent no-baseline states for empty research scopes
- Frontend component testing with Vitest and Testing Library
- Backend CI, Frontend CI, Security Gate, and Deployment Validation workflows

## API direction

The target API surface is organized around research, evidence, knowledge, education, administration, and platform operations. Authenticated routes use bearer tokens obtained through the authentication API.

The repository currently retains older market, watchlist, portfolio, alert, and ticker-oriented research endpoints. They are considered legacy until a separate architecture decision determines whether each endpoint should be removed, archived, or adapted into a general research example.

## Engineering workflow

Changes should be delivered through focused pull requests and must pass the repository's required quality gates:

- Backend tests and validation
- Frontend tests, type checking, application build, and production container build
- Security Gate
- Deployment Validation
- Documentation updates when behavior or setup changes

Tests should cover successful, loading, empty, unauthorized, not-found, and failed states where those states exist. User-visible status must not rely on color alone.

## Near-term priorities

1. Remove or isolate obsolete trading-era product assumptions.
2. Expand automated coverage across authentication, API proxies, and race conditions.
3. Improve request cancellation and stale-data handling in asynchronous dashboards.
4. Continue building the research, validation, knowledge, and education workflows around transparent human oversight.

## Legacy financial modules

Legacy financial functionality may include market quotes, company news, watchlists, portfolios, holdings analytics, alerts, and ticker-based research. Its presence in the repository does not indicate that LionsForge AI is an active trading platform. No live trading capability should be introduced without a new, explicit product decision and appropriate security, risk, legal, and regulatory review.

## License and contribution status

Contribution and licensing guidance should be added before broader external distribution. Until then, repository changes should follow existing branch protections, review expectations, and automated checks.
