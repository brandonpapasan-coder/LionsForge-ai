from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.executive_brief_snapshot import ExecutiveBriefSnapshot
from app.models.knowledge_memory import KnowledgeMemory
from app.models.mission import Mission
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.knowledge_memory import (
    KnowledgeMemoryPromotionResult,
    KnowledgeMemoryRead,
    KnowledgeMemorySynthesis,
    KnowledgeMemoryUpdate,
)
from app.services.knowledge_memory_service import (
    list_memories,
    promote_completed_mission,
    revisions_for,
    supersede_memory,
    update_memory,
)
from app.services.user_authored_memory_service import validate_user_authored_revision

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


def _owned_memory(db: Session, owner_id: int, memory_id: int) -> KnowledgeMemory:
    memory = db.scalar(
        select(KnowledgeMemory).where(
            KnowledgeMemory.id == memory_id,
            KnowledgeMemory.owner_id == owner_id,
        )
    )
    if memory is None:
        raise HTTPException(status_code=404, detail="Knowledge memory not found")
    return memory


def _read(db: Session, memory: KnowledgeMemory) -> KnowledgeMemoryRead:
    return KnowledgeMemoryRead(
        **{
            column.name: getattr(memory, column.name)
            for column in KnowledgeMemory.__table__.columns
        },
        revisions=revisions_for(db, memory.id),
    )


@router.post(
    "/projects/{project_id}/promote-mission/{mission_id}",
    response_model=KnowledgeMemoryPromotionResult,
)
def promote_mission_to_memory(
    project_id: int,
    mission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeMemoryPromotionResult:
    _owned_project(db, current_user.id, project_id)
    mission = db.scalar(
        select(Mission).where(
            Mission.id == mission_id,
            Mission.project_id == project_id,
            Mission.owner_id == current_user.id,
        )
    )
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found")
    if mission.final_snapshot_id is None:
        raise HTTPException(status_code=409, detail="Completed mission snapshot required")
    snapshot = db.scalar(
        select(ExecutiveBriefSnapshot).where(
            ExecutiveBriefSnapshot.id == mission.final_snapshot_id,
            ExecutiveBriefSnapshot.owner_id == current_user.id,
        )
    )
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Executive brief snapshot not found")
    try:
        memories, created, reused = promote_completed_mission(
            db,
            current_user.id,
            mission,
            snapshot,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return KnowledgeMemoryPromotionResult(
        memories=[_read(db, memory) for memory in memories],
        created_count=created,
        reused_count=reused,
    )


@router.get("", response_model=list[KnowledgeMemoryRead])
def get_knowledge_memories(
    project_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    mission_id: int | None = Query(default=None),
    snapshot_id: int | None = Query(default=None),
    evidence_id: int | None = Query(default=None),
    query: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[KnowledgeMemoryRead]:
    memories = list_memories(
        db,
        current_user.id,
        project_id=project_id,
        status=status,
        category=category,
        mission_id=mission_id,
        snapshot_id=snapshot_id,
        evidence_id=evidence_id,
        query=query,
    )
    return [_read(db, memory) for memory in memories]


@router.get(
    "/projects/{project_id}/synthesis",
    response_model=KnowledgeMemorySynthesis,
)
def synthesize_project_memory(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeMemorySynthesis:
    _owned_project(db, current_user.id, project_id)
    memories = list_memories(db, current_user.id, project_id=project_id)
    grouped = {
        state: []
        for state in ("validated", "provisional", "contested", "superseded")
    }
    for memory in memories:
        if memory.status in grouped:
            grouped[memory.status].append(_read(db, memory))
    return KnowledgeMemorySynthesis(
        project_id=project_id,
        validated=grouped["validated"],
        provisional=grouped["provisional"],
        contested=grouped["contested"],
        superseded=grouped["superseded"],
        agreements=[item.statement for item in memories if item.status == "validated"],
        contradictions=[item.statement for item in memories if item.status == "contested"],
        unresolved_questions=list(
            dict.fromkeys(
                question
                for item in memories
                for question in item.provenance.get("unresolved_questions", [])
            )
        ),
    )


@router.get("/{memory_id}", response_model=KnowledgeMemoryRead)
def get_knowledge_memory(
    memory_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeMemoryRead:
    return _read(db, _owned_memory(db, current_user.id, memory_id))


@router.patch("/{memory_id}", response_model=KnowledgeMemoryRead)
def revise_knowledge_memory(
    memory_id: int,
    payload: KnowledgeMemoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeMemoryRead:
    memory = _owned_memory(db, current_user.id, memory_id)
    changes = payload.model_dump(exclude_unset=True)
    try:
        validate_user_authored_revision(memory, changes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    requested_confidence = changes.get("confidence", memory.confidence)
    if changes.get("status") == "validated" and requested_confidence < 0.5:
        raise HTTPException(
            status_code=422,
            detail="Validated memory requires confidence of at least 0.5",
        )
    memory = update_memory(db, memory, changes)
    return _read(db, memory)


@router.post("/{memory_id}/archive", response_model=KnowledgeMemoryRead)
def archive_knowledge_memory(
    memory_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeMemoryRead:
    memory = _owned_memory(db, current_user.id, memory_id)
    if memory.status == "superseded":
        raise HTTPException(status_code=409, detail="Superseded memory cannot be archived")
    if memory.status != "archived":
        memory = update_memory(db, memory, {"status": "archived"})
    return _read(db, memory)


@router.post("/{memory_id}/restore", response_model=KnowledgeMemoryRead)
def restore_knowledge_memory(
    memory_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeMemoryRead:
    memory = _owned_memory(db, current_user.id, memory_id)
    if memory.status != "archived":
        raise HTTPException(status_code=409, detail="Only archived memory can be restored")
    memory = update_memory(db, memory, {"status": "provisional"})
    return _read(db, memory)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_memory(
    memory_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    memory = _owned_memory(db, current_user.id, memory_id)
    db.delete(memory)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{memory_id}/supersede/{replacement_id}",
    response_model=KnowledgeMemoryRead,
)
def supersede_knowledge_memory(
    memory_id: int,
    replacement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KnowledgeMemoryRead:
    memory = _owned_memory(db, current_user.id, memory_id)
    replacement = _owned_memory(db, current_user.id, replacement_id)
    try:
        memory = supersede_memory(db, memory, replacement)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _read(db, memory)
