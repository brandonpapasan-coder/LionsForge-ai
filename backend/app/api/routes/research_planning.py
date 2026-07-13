from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.mission import Mission
from app.models.research_planning import ResearchPlanRecommendation, ResearchPlanRevision
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.mission import MissionRead
from app.schemas.research_planning import (
    ResearchPlanGenerationResult,
    ResearchPlanRecommendationRead,
    ResearchPlanUpdate,
    ResearchRoadmap,
)
from app.services.research_planning_service import (
    generate_project_recommendations,
    list_recommendations,
)

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


def _owned_recommendation(
    db: Session,
    owner_id: int,
    recommendation_id: int,
) -> ResearchPlanRecommendation:
    recommendation = db.scalar(
        select(ResearchPlanRecommendation).where(
            ResearchPlanRecommendation.id == recommendation_id,
            ResearchPlanRecommendation.owner_id == owner_id,
        )
    )
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Research recommendation not found")
    return recommendation


def _revisions(db: Session, recommendation_id: int) -> list[ResearchPlanRevision]:
    return list(
        db.scalars(
            select(ResearchPlanRevision)
            .where(ResearchPlanRevision.recommendation_id == recommendation_id)
            .order_by(ResearchPlanRevision.revision_number)
        ).all()
    )


def _read(
    db: Session,
    recommendation: ResearchPlanRecommendation,
) -> ResearchPlanRecommendationRead:
    return ResearchPlanRecommendationRead(
        **{
            column.name: getattr(recommendation, column.name)
            for column in ResearchPlanRecommendation.__table__.columns
        },
        revisions=_revisions(db, recommendation.id),
    )


def _append_revision(db: Session, item: ResearchPlanRecommendation) -> None:
    db.add(
        ResearchPlanRevision(
            recommendation_id=item.id,
            revision_number=item.revision_number,
            recommendation_type=item.recommendation_type,
            title=item.title,
            rationale=item.rationale,
            recommended_action=item.recommended_action,
            priority_score=item.priority_score,
            priority_components=item.priority_components,
            status=item.status,
            mission_id=item.mission_id,
            provenance=item.provenance,
        )
    )


@router.post(
    "/projects/{project_id}/generate",
    response_model=ResearchPlanGenerationResult,
)
def generate_research_plan(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchPlanGenerationResult:
    _owned_project(db, current_user.id, project_id)
    recommendations, created, reused = generate_project_recommendations(
        db,
        current_user.id,
        project_id,
    )
    return ResearchPlanGenerationResult(
        recommendations=[_read(db, item) for item in recommendations],
        created_count=created,
        reused_count=reused,
    )


@router.get("", response_model=list[ResearchPlanRecommendationRead])
def get_research_plan_recommendations(
    project_id: int | None = Query(default=None),
    recommendation_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ResearchPlanRecommendationRead]:
    return [
        _read(db, item)
        for item in list_recommendations(
            db,
            current_user.id,
            project_id=project_id,
            recommendation_type=recommendation_type,
            status=status,
        )
    ]


@router.get(
    "/projects/{project_id}/roadmap",
    response_model=ResearchRoadmap,
)
def get_research_roadmap(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchRoadmap:
    _owned_project(db, current_user.id, project_id)
    recommendations = list_recommendations(
        db,
        current_user.id,
        project_id=project_id,
    )
    grouped = {
        state: []
        for state in ("proposed", "accepted", "completed", "dismissed", "archived")
    }
    for item in recommendations:
        grouped.setdefault(item.status, []).append(_read(db, item))
    return ResearchRoadmap(
        project_id=project_id,
        total_recommendations=len(recommendations),
        proposed=grouped["proposed"],
        accepted=grouped["accepted"],
        completed=grouped["completed"],
        dismissed=grouped["dismissed"],
        archived=grouped["archived"],
        top_priorities=[_read(db, item) for item in recommendations[:5]],
    )


@router.get("/{recommendation_id}", response_model=ResearchPlanRecommendationRead)
def get_research_recommendation(
    recommendation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchPlanRecommendationRead:
    return _read(
        db,
        _owned_recommendation(db, current_user.id, recommendation_id),
    )


@router.patch("/{recommendation_id}", response_model=ResearchPlanRecommendationRead)
def revise_research_recommendation(
    recommendation_id: int,
    payload: ResearchPlanUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchPlanRecommendationRead:
    item = _owned_recommendation(db, current_user.id, recommendation_id)
    changed = False
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None and getattr(item, key) != value:
            setattr(item, key, value)
            changed = True
    if changed:
        item.revision_number += 1
        _append_revision(db, item)
        db.commit()
        db.refresh(item)
    return _read(db, item)


@router.post(
    "/{recommendation_id}/create-mission-draft",
    response_model=MissionRead,
)
def create_mission_draft_from_recommendation(
    recommendation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MissionRead:
    item = _owned_recommendation(db, current_user.id, recommendation_id)
    if item.status != "accepted":
        raise HTTPException(
            status_code=409,
            detail="Recommendation must be accepted before mission draft creation",
        )
    if item.mission_id is not None:
        mission = db.scalar(
            select(Mission).where(
                Mission.id == item.mission_id,
                Mission.owner_id == current_user.id,
            )
        )
        if mission is not None:
            return MissionRead.model_validate(mission)

    mission = Mission(
        owner_id=current_user.id,
        project_id=item.project_id,
        title=item.title[:200],
        objective=item.recommended_action,
        success_criteria=[
            "Address the recommendation rationale",
            "Collect traceable supporting and contradictory evidence",
            "Produce a reviewable executive snapshot",
        ],
        status="draft",
    )
    db.add(mission)
    db.flush()
    item.mission_id = mission.id
    item.revision_number += 1
    _append_revision(db, item)
    db.commit()
    db.refresh(mission)
    return MissionRead.model_validate(mission)
