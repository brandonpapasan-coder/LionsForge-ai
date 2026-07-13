from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.executive_brief_snapshot import ExecutiveBriefSnapshot
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.executive_intelligence import (
    ExecutiveBriefSnapshotComparison,
    ExecutiveBriefSnapshotCreateResult,
    ExecutiveBriefSnapshotRead,
    ExecutiveIntelligenceBriefRead,
)
from app.services.executive_brief_snapshot_service import (
    compare_snapshots,
    create_snapshot,
    list_project_snapshots,
)
from app.services.executive_intelligence_service import build_executive_brief

router = APIRouter()


def _owned_project(db: Session, owner_id: int, project_id: int) -> ResearchProject:
    project = db.scalar(
        select(ResearchProject).where(
            ResearchProject.id == project_id,
            ResearchProject.owner_id == owner_id,
        )
    )
    if project is None:
        raise HTTPException(status_code=404, detail="Research project not found")
    return project


def _owned_snapshot(db: Session, owner_id: int, snapshot_id: int) -> ExecutiveBriefSnapshot:
    snapshot = db.scalar(
        select(ExecutiveBriefSnapshot).where(
            ExecutiveBriefSnapshot.id == snapshot_id,
            ExecutiveBriefSnapshot.owner_id == owner_id,
        )
    )
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Executive brief snapshot not found")
    return snapshot


@router.get("/projects/{project_id}", response_model=ExecutiveIntelligenceBriefRead)
def get_executive_intelligence_brief(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExecutiveIntelligenceBriefRead:
    project = _owned_project(db, current_user.id, project_id)
    return ExecutiveIntelligenceBriefRead(**build_executive_brief(db, current_user.id, project))


@router.post(
    "/projects/{project_id}/snapshots",
    response_model=ExecutiveBriefSnapshotCreateResult,
    status_code=status.HTTP_201_CREATED,
)
def generate_executive_brief_snapshot(
    project_id: int,
    force: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExecutiveBriefSnapshotCreateResult:
    project = _owned_project(db, current_user.id, project_id)
    snapshot, created = create_snapshot(db, current_user.id, project, force)
    return ExecutiveBriefSnapshotCreateResult(snapshot=snapshot, created=created)


@router.get("/projects/{project_id}/snapshots", response_model=list[ExecutiveBriefSnapshotRead])
def get_executive_brief_snapshot_history(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ExecutiveBriefSnapshot]:
    _owned_project(db, current_user.id, project_id)
    return list_project_snapshots(db, current_user.id, project_id)


@router.get("/snapshots/{snapshot_id}", response_model=ExecutiveBriefSnapshotRead)
def get_executive_brief_snapshot(
    snapshot_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExecutiveBriefSnapshot:
    return _owned_snapshot(db, current_user.id, snapshot_id)


@router.get(
    "/snapshots/{left_id}/compare/{right_id}",
    response_model=ExecutiveBriefSnapshotComparison,
)
def compare_executive_brief_snapshots(
    left_id: int,
    right_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExecutiveBriefSnapshotComparison:
    left = _owned_snapshot(db, current_user.id, left_id)
    right = _owned_snapshot(db, current_user.id, right_id)
    if left.project_id != right.project_id:
        raise HTTPException(status_code=422, detail="Snapshots must belong to the same project")
    return ExecutiveBriefSnapshotComparison(**compare_snapshots(left, right))
