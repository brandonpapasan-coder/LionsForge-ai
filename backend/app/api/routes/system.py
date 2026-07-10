from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.system_readiness import (
    ProviderHealthRead,
    ProviderHealthReport,
    ReadinessCheck,
    SystemReadinessReport,
)
from app.services.market_provider_health import provider_health_registry

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
def system_readiness_endpoint(
    db: Session = Depends(get_db),
) -> SystemReadinessReport:
    checks: list[ReadinessCheck] = []
    try:
        db.execute(text("SELECT 1"))
        checks.append(
            ReadinessCheck(
                name="database",
                status="pass",
                detail="Database connectivity verified.",
            )
        )
    except Exception as exc:
        checks.append(
            ReadinessCheck(
                name="database",
                status="fail",
                detail=f"Database readiness failed: {exc.__class__.__name__}",
            )
        )

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


@router.get("/providers", response_model=ProviderHealthReport)
def provider_health_endpoint() -> ProviderHealthReport:
    providers = []
    for name, health in sorted(provider_health_registry.snapshot().items()):
        providers.append(
            ProviderHealthRead(
                name=name,
                status=(
                    "available"
                    if provider_health_registry.is_available(name)
                    else "unavailable"
                ),
                success_count=health.success_count,
                failure_count=health.failure_count,
                consecutive_failures=health.consecutive_failures,
                error_rate=health.error_rate,
                last_latency_ms=health.last_latency_ms,
                last_error=health.last_error,
                last_success_at=health.last_success_at,
                last_failure_at=health.last_failure_at,
            )
        )
    return ProviderHealthReport(
        providers=providers,
        checked_at=datetime.now(timezone.utc),
    )
