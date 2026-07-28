from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.sandbox_payment_verification import SandboxPaymentVerificationRun
from app.models.user import User
from app.services.promotion_entitlements import PromotionConflictError, PromotionUnavailableError
from app.services.sandbox_payment_verification_orchestrator import execute_sandbox_payment_verification
from app.services.sandbox_payment_verification_readiness import derive_sandbox_verification_request

router = APIRouter()


class SandboxVerificationCreate(BaseModel):
    account_id: int = Field(gt=0)
    eligibility_id: int = Field(gt=0)
    checkout_request_id: int = Field(gt=0)
    idempotency_key: str = Field(min_length=1, max_length=128)


def _require_operator(user: User) -> None:
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operator access required")


def _serialize(run: SandboxPaymentVerificationRun) -> dict[str, object]:
    return {
        "id": run.id,
        "account_id": run.account_id,
        "eligibility_id": run.eligibility_id,
        "operator_user_id": run.operator_user_id,
        "provider": run.provider,
        "status": run.status,
        "reason_code": run.reason_code,
        "request_digest": run.request_digest,
        "provider_configuration_digest": run.provider_configuration_digest,
        "rollout_configuration_digest": run.rollout_configuration_digest,
        "checkout_request_id": run.checkout_request_id,
        "evidence_digest": run.evidence_digest,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "expires_at": run.expires_at,
    }


@router.post("/runs")
def initiate_sandbox_verification(
    payload: SandboxVerificationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    _require_operator(current_user)
    checkout_executor = getattr(request.app.state, "sandbox_checkout_executor", None)
    webhook_verifier = getattr(request.app.state, "sandbox_webhook_verifier", None)
    if checkout_executor is None or webhook_verifier is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sandbox verification adapters are not configured",
        )
    now = datetime.utcnow()
    try:
        verification_request = derive_sandbox_verification_request(
            db,
            operator_user_id=current_user.id,
            account_id=payload.account_id,
            eligibility_id=payload.eligibility_id,
            checkout_request_id=payload.checkout_request_id,
            idempotency_key=payload.idempotency_key,
            requested_at=now,
        )
        result = execute_sandbox_payment_verification(
            db,
            request=verification_request,
            checkout_request_id=payload.checkout_request_id,
            checkout_executor=checkout_executor,
            webhook_verifier=webhook_verifier,
            now=now,
        )
        db.commit()
    except PromotionConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PromotionUnavailableError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    return {
        "verification_run_id": result.verification_run_id,
        "checkout_request_id": result.checkout_request_id,
        "provider_session_id": result.provider_session_id,
        "evidence_digest": result.evidence_digest,
        "status": result.status,
    }


@router.get("/runs")
def list_sandbox_verification_runs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, object]]:
    _require_operator(current_user)
    runs = db.scalars(
        select(SandboxPaymentVerificationRun)
        .order_by(SandboxPaymentVerificationRun.started_at.desc(), SandboxPaymentVerificationRun.id.desc())
        .limit(100)
    ).all()
    return [_serialize(run) for run in runs]


@router.get("/runs/{run_id}")
def read_sandbox_verification_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    _require_operator(current_user)
    run = db.get(SandboxPaymentVerificationRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification run not found")
    return _serialize(run)
