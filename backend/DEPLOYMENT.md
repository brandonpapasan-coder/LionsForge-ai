# Backend Deployment Notes

The LionsForge AI backend is a FastAPI service.

## Local run

```bash
make install
make init-db
make run
```

## Test run

```bash
make test
```

## Container plan

The backend is ready for a container image with these high-level steps:

1. Use a Python 3.11 base image.
2. Set the working directory to the backend app directory.
3. Install dependencies from `requirements.txt`.
4. Copy backend source files into the image.
5. Start the API with Uvicorn on port 8000.

## Required environment variables

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`

For production, replace the local SQLite database with PostgreSQL and store secrets in a managed secret system.
