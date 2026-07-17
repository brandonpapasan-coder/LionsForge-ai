import json
from pathlib import Path

SCHEMA_PATH = Path("openapi.json")
REQUIRED_PATHS = {
    "/health",
    "/ready",
    "/api/v1/auth/login",
    "/api/v1/research-projects",
    "/api/v1/system/readiness",
}
LEGACY_FINANCE_PREFIXES = (
    "/api/v1/market",
    "/api/v1/market-simulator",
    "/api/v1/watchlists",
    "/api/v1/portfolios",
    "/api/v1/alerts",
    "/api/v1/advanced-alerts",
    "/api/v1/companies",
    "/api/v1/factors",
    "/api/v1/events",
    "/api/v1/decisions",
)


def main() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if not str(schema.get("openapi", "")).startswith("3."):
        raise SystemExit("OpenAPI schema version is missing or unsupported")
    if not schema.get("info", {}).get("title"):
        raise SystemExit("OpenAPI info.title is required")

    paths = set(schema.get("paths", {}))
    missing = sorted(REQUIRED_PATHS - paths)
    if missing:
        missing_paths = ", ".join(missing)
        raise SystemExit(
            f"OpenAPI schema is missing required paths: {missing_paths}"
        )

    exposed_legacy_paths = sorted(
        path
        for path in paths
        if path.startswith(LEGACY_FINANCE_PREFIXES)
    )
    if exposed_legacy_paths:
        legacy_paths = ", ".join(exposed_legacy_paths)
        raise SystemExit(
            "OpenAPI schema unexpectedly exposes legacy finance paths: "
            f"{legacy_paths}"
        )

    print(f"Validated OpenAPI contract with {len(paths)} paths")


if __name__ == "__main__":
    main()
