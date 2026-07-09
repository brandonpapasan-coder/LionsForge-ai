# Database Migrations

LionsForge AI uses Alembic for database migrations.

## Commands

```bash
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

## Current state

- Alembic configuration is present.
- Alembic environment setup is present.
- Initial user-table migration is present.
- A placeholder migration exists for the remaining product tables.

The project still includes `python -m app.db.init_db` for fast local development. Production database changes should use Alembic migrations.
