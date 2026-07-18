# Contributing to LionsForge AI

Thank you for helping improve LionsForge AI. The project is focused on AI-assisted research, evidence validation, knowledge management, and education. Contributions should strengthen transparent human oversight, provenance, security, accessibility, reliability, and maintainability.

## Product boundaries

Do not introduce live trading, brokerage connectivity, order routing, autonomous financial execution, individualized financial advice, or security-selection recommendations. Legacy finance modules are compatibility or migration candidates and must remain disabled by default unless an approved issue explicitly changes that boundary.

## Before starting

1. Search existing issues and pull requests for related work.
2. Open or reference a focused issue that defines the objective, scope, and completion criteria.
3. Keep changes narrow enough to review, test, and roll back safely.
4. Never place secrets, credentials, tokens, private keys, production data, or exploitable vulnerability details in code, commits, issues, pull requests, logs, screenshots, fixtures, or documentation.

## Development setup

### Backend

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

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

Use local-only development credentials and values. Do not reuse production or staging secrets.

## Branches and commits

- Branch from the latest `main`.
- Use a descriptive branch name such as `feature/research-workspace` or `fix/mentor-timeout`.
- Write focused commits with imperative messages.
- Avoid unrelated formatting, generated-file, or dependency changes.
- Do not rewrite shared branch history after review has begun unless reviewers agree.

## Validation

Run the checks relevant to the change before opening a pull request.

### Backend

```bash
cd backend
ruff check .
ruff format --check .
pytest
```

Also run type checking, migration validation, OpenAPI contract checks, container smoke tests, or performance smoke tests when the changed area requires them.

### Frontend

```bash
cd frontend
npm test
npx tsc --noEmit
npm run build
```

Test successful, loading, empty, unauthorized, not-found, failed, cancellation, and stale-data states when they apply. User-visible status must not rely on color alone.

## Database changes

- Use Alembic migrations for persistent schema changes.
- Make migrations deterministic, reversible when safely possible, and compatible with the documented rollout path.
- Do not silently delete or reinterpret user research, evidence, knowledge, education, or audit records.
- Document any migration boundary that affects rollback safety.

## API and AI behavior

- Keep evidence, inference, assumptions, and uncertainty distinguishable.
- Preserve provenance and revision history for consequential knowledge changes.
- Require human review for significant conclusions or actions.
- Validate authentication and owner or tenant isolation on every protected operation.
- Use deterministic, safe fallbacks when an external AI provider is unavailable.
- Do not convert raw conversation text into validated knowledge automatically.

## Pull requests

A pull request should include:

- the problem and intended outcome;
- the linked issue;
- a concise implementation summary;
- tests added or updated;
- security, privacy, accessibility, migration, and rollback considerations;
- screenshots or response examples only when they contain no private or secret data.

All required repository checks must pass before merge: Backend CI, Frontend CI, Security Gate, and Deployment Validation. Review feedback should be resolved or explicitly documented before merging.

## Documentation

Update setup, API, operational, release, or user guidance whenever behavior changes. Documentation must distinguish completed repository work from external infrastructure or manual acceptance work.

## Licensing

The repository does not currently grant an open-source license unless a `LICENSE` file is added. By submitting a contribution, you confirm that you have the right to submit it and understand that acceptance does not itself create a public license for the repository.