.PHONY: install run init-db smoke perf-smoke test clean

install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt

init-db:
	python -m app.db.init_db

run:
	uvicorn app.main:app --reload

smoke:
	python scripts/smoke_backend.py

perf-smoke:
	python scripts/performance_smoke.py

test:
	pytest

clean:
	rm -f lionsforge.db test_lionsforge.db ci_lionsforge.db docker_lionsforge.db
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
