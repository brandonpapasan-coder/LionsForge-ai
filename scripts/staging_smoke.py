#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.request


MENTOR_RESPONSE_FIELDS = {
    "conversation_id",
    "message_id",
    "intent",
    "persona",
    "answer",
    "evidence",
    "reasoning",
    "assumptions",
    "confidence",
    "confidence_reason",
    "alternative_viewpoints",
    "recommendations",
    "created_at",
}


def call(base_url, method, path, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"content-type": "application/json"}
    if token:
        headers["authorization"] = "Bearer " + token
    request = urllib.request.Request(base_url.rstrip("/") + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = response.read().decode()
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        raise RuntimeError(f"{method} {path} failed: {exc.code} {detail}") from exc


def validate_mentor_response(payload):
    missing = sorted(MENTOR_RESPONSE_FIELDS - set(payload))
    if missing:
        raise RuntimeError(f"mentor response missing fields: {', '.join(missing)}")
    if payload["confidence"] not in {"low", "medium", "high"}:
        raise RuntimeError("mentor response confidence is outside the schema")
    if not isinstance(payload["answer"], str) or not payload["answer"].strip():
        raise RuntimeError("mentor response answer is empty")
    for field in ("evidence", "reasoning", "assumptions", "alternative_viewpoints", "recommendations"):
        if not isinstance(payload[field], list):
            raise RuntimeError(f"mentor response {field} must be a list")


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

    status, providers = call(args.base_url, "GET", "/api/v1/system/providers", token=token)
    if status != 200:
        raise RuntimeError("provider health endpoint failed")
    openai_health = providers.get("providers", {}).get("openai_mentor", {})
    if openai_health.get("enabled") is not True:
        raise RuntimeError("OpenAI mentor provider is not enabled in staging")
    if openai_health.get("status") not in {"configured", "healthy"}:
        raise RuntimeError("OpenAI mentor provider is not configured or healthy")
    print("/api/v1/system/providers", {"openai_mentor": openai_health})

    status, mentor = call(
        args.base_url,
        "POST",
        "/api/v1/mentor/chat",
        {
            "message": "Explain how to separate verified evidence from assumptions in an investment research claim.",
            "context": {"goal": "staging provider validation"},
        },
        token=token,
    )
    if status != 201:
        raise RuntimeError("staging mentor request failed")
    validate_mentor_response(mentor)
    print(
        "/api/v1/mentor/chat",
        {
            "intent": mentor["intent"],
            "persona": mentor["persona"],
            "confidence": mentor["confidence"],
            "schema_valid": True,
        },
    )

    print(json.dumps({"status": "passed", "openai_mentor": "enabled", "mentor_schema": "valid"}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"staging smoke failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
