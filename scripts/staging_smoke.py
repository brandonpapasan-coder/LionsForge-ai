#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def call(base_url, method, path, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"content-type": "application/json"}
    if token:
        headers["authorization"] = "Bearer " + token
    request = urllib.request.Request(base_url.rstrip("/") + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode()
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        raise RuntimeError(f"{method} {path} failed: {exc.code} {detail}") from exc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    email = os.environ["STAGING_TEST_EMAIL"]
    secret = os.environ["STAGING_TEST_SECRET"]

    for path in ("/health", "/ready", "/api/v1/system/readiness"):
        status, payload = call(args.base_url, "GET", path)
        if status != 200:
            raise RuntimeError(f"{path} returned {status}")
        print(path, payload)

    status, login = call(
        args.base_url,
        "POST",
        "/api/v1/auth/login",
        {"email": email, "secret": secret, "full_name": "Staging Test"},
    )
    if status != 200:
        raise RuntimeError("staging login failed")
    token = login["access_token"]

    for path in ("/api/v1/dashboard", "/api/v1/mentor/conversations", "/api/v1/research-projects", "/api/v1/education"):
        status, payload = call(args.base_url, "GET", path, token=token)
        if status != 200:
            raise RuntimeError(f"{path} returned {status}")
        print(path, payload)

    print(json.dumps({"status": "passed"}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"staging smoke failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
