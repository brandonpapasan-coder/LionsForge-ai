import json
from pathlib import Path

SCHEMA_PATH = Path("openapi.json")
REQUIRED_PATHS = {
    "/health",
    "/ready",
    "/platform",
    "/api/v1/auth/login",
    "/api/v1/portfolios/{portfolio_id}/intelligence",
    "/api/v1/system/readiness",
    "/api/v1/system/providers",
    "/api/v1/system/metrics",
}
REQUIRED_METHODS = {
    "/health": {"get"},
    "/ready": {"get"},
    "/platform": {"get"},
    "/api/v1/auth/login": {"post"},
    "/api/v1/portfolios/{portfolio_id}/intelligence": {"get"},
    "/api/v1/system/readiness": {"get"},
    "/api/v1/system/providers": {"get"},
    "/api/v1/system/metrics": {"get"},
}


def main() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if not str(schema.get("openapi", "")).startswith("3."):
        raise SystemExit("OpenAPI schema version is missing or unsupported")
    if not schema.get("info", {}).get("title"):
        raise SystemExit("OpenAPI info.title is required")

    schema_paths = schema.get("paths", {})
    paths = set(schema_paths)
    missing = sorted(REQUIRED_PATHS - paths)
    if missing:
        missing_paths = ", ".join(missing)
        raise SystemExit(f"OpenAPI schema is missing required paths: {missing_paths}")

    method_failures = []
    for path, required_methods in sorted(REQUIRED_METHODS.items()):
        actual_methods = set(schema_paths[path])
        missing_methods = sorted(required_methods - actual_methods)
        if missing_methods:
            method_failures.append(f"{path}: {', '.join(missing_methods)}")
    if method_failures:
        raise SystemExit(
            "OpenAPI schema is missing required methods: " + "; ".join(method_failures)
        )

    print(
        f"Validated OpenAPI contract with {len(paths)} paths and "
        f"{sum(len(methods) for methods in REQUIRED_METHODS.values())} required methods"
    )


if __name__ == "__main__":
    main()
