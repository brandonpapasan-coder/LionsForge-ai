from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.observability import error_event_registry, request_metrics_registry
from app.db.session import get_db
from app.models.user import User
from app.schemas.system_readiness import (
    ErrorEventRead,
    OperationalMetricsReport,
    ReadinessCheck,
    SystemReadinessReport,
)
from app.services.openai_mentor import OpenAIMentorProvider

router = APIRouter()

ACTIVE_PLATFORM_MODULES = [
    "research-orchestration",
    "evidence-validation",
    "knowledge-graph",
    "knowledge-memory",
    "education",
    "mentor",
    "missions",
    "multi-agent-consensus",
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
            name="active_modules",
            status="pass",
            detail=f"{len(ACTIVE_PLATFORM_MODULES)} active research and education modules registered.",
        )
    )
    status = "ready" if all(check.status == "pass" for check in checks) else "degraded"
    return SystemReadinessReport(
        status=status,
        release="RC3",
        checks=checks,
        modules=ACTIVE_PLATFORM_MODULES,
        checked_at=datetime.now(timezone.utc),
    )


@router.get("/providers")
def provider_health_endpoint(
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    del current_user
    provider = OpenAIMentorProvider()
    return {
        "providers": {"openai_mentor": provider.health()},
        "checked_at": datetime.now(timezone.utc),
    }


@router.get("/metrics", response_model=OperationalMetricsReport)
def operational_metrics_endpoint(
    current_user: User = Depends(get_current_user),
) -> OperationalMetricsReport:
    del current_user
    request_snapshot = request_metrics_registry.snapshot()
    error_snapshot = error_event_registry.snapshot()
    last_event = error_snapshot["last_event"]
    return OperationalMetricsReport(
        request_count=request_snapshot["request_count"],
        server_error_count=request_snapshot["error_count"],
        average_duration_ms=request_snapshot["average_duration_ms"],
        status_codes=request_snapshot["status_codes"],
        application_exception_count=error_snapshot["total_count"],
        exceptions_by_type=error_snapshot["by_exception_type"],
        last_exception=(
            ErrorEventRead(
                request_id=last_event.request_id,
                method=last_event.method,
                path=last_event.path,
                exception_type=last_event.exception_type,
                occurred_at=last_event.occurred_at,
            )
            if last_event is not None
            else None
        ),
        checked_at=datetime.now(timezone.utc),
    )
