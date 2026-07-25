#!/usr/bin/env python3
"""Validate staging prerequisites without changing infrastructure."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

AWS_REGION_RE = re.compile(r"^[a-z]{2}(?:-gov)?-[a-z]+-\d$")
IAM_ROLE_ARN_RE = re.compile(r"^arn:(aws|aws-us-gov):iam::\d{12}:role/[A-Za-z0-9+=,.@_/-]{1,512}$")
BUCKET_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{1,61}[a-z0-9])?$")
LOCAL_HOSTS = {"localhost", "localhost.localdomain"}


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


def validate_origin(name: str, value: str) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise RuntimeError(f"{name} must be an absolute HTTPS origin")
    if parsed.username or parsed.password:
        raise RuntimeError(f"{name} must not contain credentials")
    if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
        raise RuntimeError(f"{name} must not contain a path, parameters, query, or fragment")
    if parsed.port not in {None, 443}:
        raise RuntimeError(f"{name} must use the default HTTPS port")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in LOCAL_HOSTS or hostname.endswith(".localhost"):
        raise RuntimeError(f"{name} must not use a local hostname")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address and not address.is_global:
        raise RuntimeError(f"{name} must not use a non-public IP address")
    if "." not in hostname and address is None:
        raise RuntimeError(f"{name} must use a fully qualified hostname")
    return parsed


def validate_configuration(values: dict[str, str]) -> dict[str, str]:
    region = values["AWS_REGION"]
    if not AWS_REGION_RE.fullmatch(region):
        raise RuntimeError("AWS_REGION must use a canonical AWS region identifier")

    plan_role = values["AWS_TERRAFORM_PLAN_ROLE_ARN"]
    apply_role = values["AWS_TERRAFORM_APPLY_ROLE_ARN"]
    if not IAM_ROLE_ARN_RE.fullmatch(plan_role):
        raise RuntimeError("AWS_TERRAFORM_PLAN_ROLE_ARN must be a valid IAM role ARN")
    if not IAM_ROLE_ARN_RE.fullmatch(apply_role):
        raise RuntimeError("AWS_TERRAFORM_APPLY_ROLE_ARN must be a valid IAM role ARN")
    if plan_role == apply_role:
        raise RuntimeError("plan and apply role ARNs must be different")

    bucket = values["TF_STATE_BUCKET"]
    if not BUCKET_RE.fullmatch(bucket) or ".." in bucket or ".-" in bucket or "-." in bucket:
        raise RuntimeError("TF_STATE_BUCKET must be a valid lowercase S3 bucket name")
    if not bucket.startswith("lionsforge-"):
        raise RuntimeError("TF_STATE_BUCKET must use the LionsForge state bucket naming convention")

    api = validate_origin("STAGING_API_URL", values["STAGING_API_URL"])
    web = validate_origin("STAGING_WEB_URL", values["STAGING_WEB_URL"])
    assert api.hostname and web.hostname
    if api.hostname.rstrip(".").lower() == web.hostname.rstrip(".").lower():
        raise RuntimeError("STAGING_API_URL and STAGING_WEB_URL must use distinct hosts")

    return {
        "aws_region": region,
        "state_bucket": bucket,
        "api_origin": values["STAGING_API_URL"].rstrip("/"),
        "web_origin": values["STAGING_WEB_URL"].rstrip("/"),
    }


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
    configuration = validate_configuration(values)
    report: dict[str, object] = {
        "configuration": {
            **configuration,
            "plan_apply_roles_separated": True,
        }
    }

    if not args.skip_endpoints:
        api_url = configuration["api_origin"]
        web_url = configuration["web_origin"]
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
