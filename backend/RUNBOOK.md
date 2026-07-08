# Backend Runbook

## Fresh local run

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
make smoke
make test
make run
```

## Reset stale local SQLite state

```bash
rm -f lionsforge.db test_lionsforge.db ci_lionsforge.db
make smoke
make test
```

## Common startup issues

### Missing email validation dependency

If startup fails while importing `EmailStr`, reinstall dependencies:

```bash
pip install -r requirements.txt
```

### Stale database schema

If routes fail with missing table or missing column errors, reset the local SQLite files and rerun the smoke check.

### Production Postgres driver

The production example uses a `postgresql+psycopg://` database URL. Production deployments need the matching psycopg driver installed in the runtime image.

### Provider configuration

Local development should use:

```bash
MARKET_DATA_PROVIDER=mock
NEWS_PROVIDER=mock
```

Live provider names require matching API keys.
