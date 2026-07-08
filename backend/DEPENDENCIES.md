# Backend Dependencies

## Core runtime

Installed from `requirements.txt`:

- FastAPI and Uvicorn
- Pydantic and pydantic-settings
- SQLAlchemy and Alembic
- Auth and form parsing dependencies
- Test dependencies used by CI

## Local database

Local development defaults to SQLite and does not require an external database driver.

## Production database

Production should install a Postgres driver compatible with the chosen `DATABASE_URL` format.

Common options:

- `psycopg[binary]` for modern psycopg 3 deployments
- `psycopg2-binary` for legacy psycopg 2 deployments

Keep the production image and `DATABASE_URL` aligned.
