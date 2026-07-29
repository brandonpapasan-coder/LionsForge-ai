#!/usr/bin/env python3
"""Validate the complete public-operations evidence authorization chain."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")
TOP = {
    "schema",
    "schema_version",
    "candidate_sha",
    "decision",
    "activation_mode",
    "manifest_path",
    "manifest_sha256",
    "binding_path",
    "binding_sha256",
    "receipt_path",
    "receipt_sha256",
    "ledger_path",
    "ledger_sha256",
    "aggregate_evidence_sha256",
    "authorization_digest",
    "receipt_id",
}
FORBIDDEN = ("password", "secret", "token", "api_key", "private_key", "credential")


def _scan_secrets(value: object) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if any(fragment in key.lower() for fragment in FORBIDDEN):
                raise ValueError(f"forbidden secret-like key: {key}")
            _scan_secrets(nested)
    elif isinstance(value, list):
        for nested in value:
            _scan_secrets(nested)


def _safe_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not SAFE_PATH.fullmatch(value):
        raise ValueError(f"{label} is invalid")
    if value.startswith("/") or ".." in value.split("/"):
        raise ValueError(f"{label} is unsafe")
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise ValueError(f"{label} is invalid")
    return value


def _load_bound(root: Path, path_value: object, digest_value: object, label: str) -> tuple[dict[str, object], str]:
    relative = _safe_path(path_value, f"{label}_path")
    expected = _digest(digest_value, f"{label}_sha256")
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} file is missing or unsafe")
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ValueError(f"{label} digest mismatch")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    _scan_secrets(value)
    return value, actual


def _require_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label} mismatch")


def validate_reconciliation(value: object, root: Path, expected_candidate: str | None = None) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != TOP:
        raise ValueError("top-level keys do not match contract")
    _scan_secrets(value)
    if value["schema"] != "lionsforge.public-operations-evidence-reconciliation" or value["schema_version"] != 1:
        raise ValueError("schema is invalid")

    candidate = value["candidate_sha"]
    if not isinstance(candidate, str) or not SHA40.fullmatch(candidate):
        raise ValueError("candidate_sha is invalid")
    if expected_candidate and candidate != expected_candidate:
        raise ValueError("candidate does not match expected candidate")

    decision = value["decision"]
    mode = value["activation_mode"]
    if decision not in {"GO", "NO-GO"}:
        raise ValueError("decision is invalid")
    if mode not in {"NONE", "CONTROLLED-BETA", "GENERAL-AVAILABILITY"}:
        raise ValueError("activation_mode is invalid")
    if decision == "NO-GO" and mode != "NONE":
        raise ValueError("NO-GO requires activation mode NONE")
    if decision == "GO" and mode == "NONE":
        raise ValueError("GO requires an activation mode")

    aggregate = _digest(value["aggregate_evidence_sha256"], "aggregate_evidence_sha256")
    authorization = _digest(value["authorization_digest"], "authorization_digest")
    receipt_id = value["receipt_id"]
    if not isinstance(receipt_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]{8,96}", receipt_id):
        raise ValueError("receipt_id is invalid")

    manifest, manifest_digest = _load_bound(root, value["manifest_path"], value["manifest_sha256"], "manifest")
    binding, binding_digest = _load_bound(root, value["binding_path"], value["binding_sha256"], "binding")
    receipt, receipt_digest = _load_bound(root, value["receipt_path"], value["receipt_sha256"], "receipt")
    ledger, ledger_digest = _load_bound(root, value["ledger_path"], value["ledger_sha256"], "ledger")

    for artifact_name, artifact in (("manifest", manifest), ("binding", binding), ("receipt", receipt)):
        _require_equal(artifact.get("candidate_sha"), candidate, f"{artifact_name} candidate")
    for artifact_name, artifact in (("binding", binding), ("receipt", receipt)):
        _require_equal(artifact.get("decision"), decision, f"{artifact_name} decision")
        _require_equal(artifact.get("activation_mode"), mode, f"{artifact_name} activation mode")
        _require_equal(artifact.get("aggregate_evidence_sha256"), aggregate, f"{artifact_name} aggregate evidence")

    _require_equal(binding.get("manifest_sha256"), manifest_digest, "binding manifest digest")
    _require_equal(receipt.get("binding_sha256"), binding_digest, "receipt binding digest")
    _require_equal(receipt.get("authorization_digest"), authorization, "receipt authorization digest")
    _require_equal(receipt.get("receipt_id"), receipt_id, "receipt id")

    entries = ledger.get("entries")
    if not isinstance(entries, list):
        raise ValueError("ledger entries must be a list")
    matches = [entry for entry in entries if isinstance(entry, dict) and entry.get("receipt_id") == receipt_id]
    if len(matches) != 1:
        raise ValueError("ledger must contain exactly one matching receipt")
    entry = matches[0]
    _require_equal(entry.get("candidate_sha"), candidate, "ledger candidate")
    _require_equal(entry.get("decision"), decision, "ledger decision")
    _require_equal(entry.get("activation_mode"), mode, "ledger activation mode")
    _require_equal(entry.get("receipt_sha256"), receipt_digest, "ledger receipt digest")
    _require_equal(entry.get("authorization_digest"), authorization, "ledger authorization digest")

    summary = {
        "activation_mode": mode,
        "authorization_digest": authorization,
        "candidate_sha": candidate,
        "decision": decision,
        "ledger_sha256": ledger_digest,
        "manifest_sha256": manifest_digest,
        "receipt_id": receipt_id,
        "result": "VALID",
    }
    summary["reconciliation_digest"] = hashlib.sha256(
        json.dumps(summary, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--expected-candidate")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        record = json.loads(Path(args.record).read_text(encoding="utf-8"))
        result = validate_reconciliation(record, Path(args.repository_root).resolve(), args.expected_candidate)
        if args.output:
            Path(args.output).write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"public operations evidence reconciliation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
