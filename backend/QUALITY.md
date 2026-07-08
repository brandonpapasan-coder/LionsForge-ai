# Backend Code Quality

The backend is configured for Ruff.

Recommended local commands:

```bash
ruff check .
ruff format .
pytest
```

Quality gates to add in CI once the lint dependency is installed:

```bash
ruff check .
pytest
```
