# Contributing to LionsForge AI

## Development workflow

1. Create a feature branch from `main`.
2. Make focused commits.
3. Run backend tests before opening a pull request.
4. Open a pull request with a clear summary and test notes.

## Backend setup

```bash
cd backend
make install
make init-db
make run
```

## Tests

```bash
cd backend
make test
```

## Pull request checklist

- Code is scoped to one clear change.
- Tests were added or updated when needed.
- Security-sensitive changes were reviewed.
- No real secrets were committed.
