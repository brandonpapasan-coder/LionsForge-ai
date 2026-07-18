from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.release_countdown import (
    ReleaseCountdownCheckpoint,
    ReleaseCountdownPhase,
    ReleaseCountdownSummary,
)

router = APIRouter()
DISCLAIMER = (
    "The countdown reports verified checkpoint completion, not a calendar estimate. "
    "External staging work remains incomplete until infrastructure and acceptance evidence are recorded."
)


def _checkpoint(
    key: str,
    label: str,
    state: str,
    *,
    external: bool = False,
    issue_number: int | None = None,
) -> ReleaseCountdownCheckpoint:
    return ReleaseCountdownCheckpoint(
        key=key,
        label=label,
        state=state,
        external=external,
        issue_number=issue_number,
    )


def _phase(
    key: str,
    label: str,
    weight: int,
    completed_points: int,
    state: str,
    checkpoints: list[ReleaseCountdownCheckpoint],
) -> ReleaseCountdownPhase:
    return ReleaseCountdownPhase(
        key=key,
        label=label,
        weight=weight,
        completed_points=completed_points,
        completion_percent=round((completed_points / weight) * 100) if weight else 0,
        state=state,
        checkpoints=checkpoints,
    )


@router.get("", response_model=ReleaseCountdownSummary)
def get_release_countdown(
    current_user: User = Depends(get_current_user),
) -> ReleaseCountdownSummary:
    _ = current_user
    phases = [
        _phase(
            "product",
            "Product implementation",
            72,
            72,
            "complete",
            [
                _checkpoint("research", "Research assistant workflows", "complete"),
                _checkpoint("education", "Education and mentor workflows", "complete"),
                _checkpoint("evidence", "Evidence validation and remediation", "complete"),
                _checkpoint("memory", "Saved-record memory and audit history", "complete"),
                _checkpoint("governance", "Governance, trust, and export integrity", "complete"),
                _checkpoint("owner-scope", "Authentication and owner isolation", "complete"),
            ],
        ),
        _phase(
            "repository",
            "Repository release preparation",
            18,
            18,
            "complete",
            [
                _checkpoint("backend-ci", "Backend CI and contract validation", "complete"),
                _checkpoint("frontend-ci", "Frontend CI, type checks, and production build", "complete"),
                _checkpoint("security", "Security scanning and SBOM generation", "complete"),
                _checkpoint("deployment-validation", "Kubernetes deployment validation", "complete"),
                _checkpoint("staging-workflow", "Staging deployment automation and runbook", "complete"),
            ],
        ),
        _phase(
            "staging",
            "External staging provisioning",
            5,
            0,
            "blocked",
            [
                _checkpoint("cluster", "Provision Kubernetes staging cluster and namespace", "blocked", external=True, issue_number=29),
                _checkpoint("network", "Configure ingress, DNS, and HTTPS", "remaining", external=True, issue_number=29),
                _checkpoint("database", "Provision staging PostgreSQL and backup path", "remaining", external=True, issue_number=29),
                _checkpoint("github-environment", "Configure staging secrets and STAGING_API_URL", "remaining", external=True, issue_number=29),
                _checkpoint("observability", "Configure staging logs, metrics, and alerts", "remaining", external=True, issue_number=29),
            ],
        ),
        _phase(
            "acceptance",
            "Final staging acceptance",
            5,
            0,
            "remaining",
            [
                _checkpoint("deploy", "Deploy an immutable green release SHA", "remaining", external=True, issue_number=29),
                _checkpoint("journey", "Complete authenticated product acceptance journey", "remaining", external=True, issue_number=29),
                _checkpoint("persistence", "Verify sign-in persistence and saved state", "remaining", external=True, issue_number=29),
                _checkpoint("rollback", "Verify backup, restore, and safe rollback", "remaining", external=True, issue_number=29),
                _checkpoint("go", "Record named-owner GO decision", "remaining", external=True, issue_number=29),
            ],
        ),
    ]
    checkpoints = [checkpoint for phase in phases for checkpoint in phase.checkpoints]
    completed_points = sum(phase.completed_points for phase in phases)
    total_points = sum(phase.weight for phase in phases)
    remaining = [item for item in checkpoints if item.state != "complete"]
    return ReleaseCountdownSummary(
        overall_completion_percent=round((completed_points / total_points) * 100),
        completed_points=completed_points,
        remaining_points=total_points - completed_points,
        total_points=total_points,
        completed_checkpoints=sum(item.state == "complete" for item in checkpoints),
        remaining_checkpoints=len(remaining),
        blocked_checkpoints=sum(item.state == "blocked" for item in checkpoints),
        external_checkpoints=sum(item.external and item.state != "complete" for item in checkpoints),
        remaining_milestones=1,
        current_blocker="Issue #29: external staging infrastructure and GitHub environment configuration",
        next_action="Provision the Kubernetes staging cluster and lionsforge-staging namespace.",
        phases=phases,
        disclaimer=DISCLAIMER,
    )
