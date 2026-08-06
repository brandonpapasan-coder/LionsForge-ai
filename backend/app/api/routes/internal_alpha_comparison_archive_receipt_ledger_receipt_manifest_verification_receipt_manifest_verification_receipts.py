import json
import unicodedata
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_current_user
from app.internal_alpha.intelligence.comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt import (
    build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt,
    validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt,
)
from app.models.user import User

router = APIRouter()

_MAX_FINDINGS = 100
_MAX_FINDING_LENGTH = 256
_TRUNCATED_FINDINGS_NOTICE = "additional validation findings omitted"
_VALIDATION_FAILURE_FINDING = "verification receipt manifest validation failed"
_INVALID_MANIFEST_DETAIL = "invalid verification receipt manifest"


class IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptInput(
    BaseModel
):
    model_config = ConfigDict(extra="forbid", strict=True)

    manifest: dict[str, Any]


class IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptValidationInput(
    BaseModel
):
    model_config = ConfigDict(extra="forbid", strict=True)

    receipt: dict[str, Any]
    manifest: dict[str, Any]


def _is_control_free(value: str) -> bool:
    return all(
        ord(character) >= 32
        and ord(character) != 127
        and not 128 <= ord(character) <= 159
        and unicodedata.category(character) not in {"Cf", "Zl", "Zp"}
        for character in value
    )


def _is_valid_findings(findings: object) -> bool:
    return type(findings) is list and all(
        type(finding) is str
        and bool(finding.strip())
        and _is_control_free(finding)
        for finding in findings
    )


def _is_valid_json_object(value: object) -> bool:
    if type(value) is not dict or any(type(key) is not str for key in value):
        return False
    try:
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError):
        return False
    return True


def _bounded_findings(findings: list[str]) -> list[str]:
    if len(findings) <= _MAX_FINDINGS:
        return [finding[:_MAX_FINDING_LENGTH] for finding in findings]

    bounded = [
        finding[:_MAX_FINDING_LENGTH]
        for finding in findings[: _MAX_FINDINGS - 1]
    ]
    bounded.append(_TRUNCATED_FINDINGS_NOTICE)
    return bounded


def _invalid_manifest_http_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=_INVALID_MANIFEST_DETAIL,
    )


@router.post(
    "/comparison/archive/receipt/manifest/bundle/receipt/ledger/receipt/manifest/verification-receipt/manifest/verification-receipt"
)
def create_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
    payload: IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Issue one deterministic receipt for a valid verification-receipt manifest."""
    del current_user
    try:
        receipt = build_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
            payload.manifest
        )
    except (TypeError, ValueError) as exc:
        raise _invalid_manifest_http_exception() from exc
    if not _is_valid_json_object(receipt):
        raise _invalid_manifest_http_exception()

    try:
        findings = validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
            receipt,
            payload.manifest,
        )
    except (TypeError, ValueError) as exc:
        raise _invalid_manifest_http_exception() from exc
    if not _is_valid_findings(findings) or findings:
        raise _invalid_manifest_http_exception()
    return receipt


@router.post(
    "/comparison/archive/receipt/manifest/bundle/receipt/ledger/receipt/manifest/verification-receipt/manifest/verification-receipt/validate"
)
def validate_internal_alpha_intelligence_comparison_archive_verification_receipt_manifest_verification_receipt(
    payload: IntelligenceComparisonArchiveVerificationReceiptManifestVerificationReceiptValidationInput,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate one receipt and its exact source-manifest binding fail closed."""
    del current_user
    try:
        findings = validate_intelligence_comparison_archive_receipt_manifest_bundle_receipt_ledger_receipt_manifest_verification_receipt_manifest_verification_receipt(
            payload.receipt,
            payload.manifest,
        )
    except (TypeError, ValueError):
        findings = [_VALIDATION_FAILURE_FINDING]
    if not _is_valid_findings(findings):
        findings = [_VALIDATION_FAILURE_FINDING]
    return {
        "valid": not findings,
        "findings": _bounded_findings(findings),
        "interpretation_notice": (
            "Receipt validity proves deterministic bounded verification-receipt manifest "
            "verification only. It does not infer causality or authorize any release transition."
        ),
    }
