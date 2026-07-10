import json
from pathlib import Path

SCHEMA_PATH = Path("openapi.json")
REQUIRED_PATHS = {
    "/health",
    "/ready",
    "/api/v1/auth/login",
    "/api/v1/portfolios/{portfolio_id}/intelligence",
    "/api/v1/system/readiness",
}


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

    print(f"Validated OpenAPI contract with {len(paths)} paths")


if __name__ == "__main__":
    main()
