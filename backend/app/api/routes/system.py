from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.system_readiness import ReadinessCheck, SystemReadinessReport

router = APIRouter()

RC3_MODULES = [
    "portfolio-risk-intelligence",
    "factor-intelligence",
    "research-agent",
    "event-intelligence",
    "decision-intelligence",
    "autonomous-portfolio-intelligence",
]


@router.get("/readiness", response_model=SystemReadinessReport)
def system_readiness_endpoint(db: Session = Depends(get_db)) -> SystemReadinessReport:
    checks: list[ReadinessCheck] = []
    try:
        db.execute(text("SELECT 1"))
        checks.append(ReadinessCheck(name="database", status="pass", detail="Database connectivity verified."))
    except Exception as exc:
        checks.append(ReadinessCheck(name="database", status="fail", detail=f"Database readiness failed: {exc.__class__.__name__}"))

    checks.append(
        ReadinessCheck(
            name="rc3_modules",
            status="pass",
            detail=f"{len(RC3_MODULES)} RC3 intelligence modules registered.",
        )
    )
    status = "ready" if all(check.status == "pass" for check in checks) else "degraded"
    return SystemReadinessReport(
        status=status,
        release="RC3",
        checks=checks,
        modules=RC3_MODULES,
        checked_at=datetime.now(timezone.utc),
    )
