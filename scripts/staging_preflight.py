#!/usr/bin/env python3
"""Validate staging prerequisites without changing infrastructure."""

from __future__ import annotations

import argparse
import json
import os
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request


def require_environment(names: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    missing: list[str] = []
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            values[name] = value
        else:
            missing.append(name)
    if missing:
        raise RuntimeError("missing required environment values: " + ", ".join(missing))
    return values


def resolve_host(url: str) -> list[str]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise RuntimeError(f"expected an HTTPS URL, received: {url}")
    addresses = sorted({item[4][0] for item in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)})
    if not addresses:
        raise RuntimeError(f"DNS resolution returned no addresses for {parsed.hostname}")
    return addresses


def check_tls(url: str) -> dict[str, str]:
    parsed = urllib.parse.urlparse(url)
    assert parsed.hostname is not None
    context = ssl.create_default_context()
    with socket.create_connection((parsed.hostname, 443), timeout=15) as raw_socket:
        with context.wrap_socket(raw_socket, server_hostname=parsed.hostname) as secure_socket:
            certificate = secure_socket.getpeercert()
            return {
                "subject": str(certificate.get("subject", "")),
                "not_after": certificate.get("notAfter", ""),
            }


def fetch(url: str, expected_status: int = 200) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"user-agent": "LionsForge-Staging-Preflight/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != expected_status:
                raise RuntimeError(f"{url} returned HTTP {response.status}, expected {expected_status}")
            body = response.read(2048).decode(errors="replace")
            return {"status": response.status, "sample": body[:200]}
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{url} returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{url} could not be reached: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-endpoints", action="store_true", help="Validate configuration only; do not call public URLs.")
    args = parser.parse_args()

    values = require_environment(
        [
            "AWS_REGION",
            "TF_STATE_BUCKET",
            "AWS_TERRAFORM_PLAN_ROLE_ARN",
            "AWS_TERRAFORM_APPLY_ROLE_ARN",
            "STAGING_API_URL",
            "STAGING_WEB_URL",
        ]
    )

    if values["AWS_TERRAFORM_PLAN_ROLE_ARN"] == values["AWS_TERRAFORM_APPLY_ROLE_ARN"]:
        raise RuntimeError("plan and apply role ARNs must be different")
    if not values["TF_STATE_BUCKET"].startswith("lionsforge-"):
        raise RuntimeError("TF_STATE_BUCKET must use the LionsForge state bucket naming convention")

    report: dict[str, object] = {
        "configuration": {
            "aws_region": values["AWS_REGION"],
            "state_bucket": values["TF_STATE_BUCKET"],
            "plan_apply_roles_separated": True,
        }
    }

    if not args.skip_endpoints:
        api_url = values["STAGING_API_URL"].rstrip("/")
        web_url = values["STAGING_WEB_URL"].rstrip("/")
        report["dns"] = {
            "api": resolve_host(api_url),
            "web": resolve_host(web_url),
        }
        report["tls"] = {
            "api": check_tls(api_url),
            "web": check_tls(web_url),
        }
        report["endpoints"] = {
            "health": fetch(api_url + "/health"),
            "readiness": fetch(api_url + "/ready"),
            "login": fetch(web_url + "/login"),
        }

    print(json.dumps({"status": "passed", "report": report}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"staging preflight failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
