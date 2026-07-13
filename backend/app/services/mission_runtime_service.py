from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import EvidenceRecord
from app.models.mission import Mission, MissionStep
from app.models.research_project import ResearchProject
from app.services.executive_brief_snapshot_service import create_snapshot
from app.services.executive_intelligence_service import build_executive_brief
from app.services.multi_agent_consensus_service import build_project_consensus
from app.services.research_trust_index_service import calculate_project_rti

METHODOLOGY_VERSION = "mission-runtime-v1"
STEP_PLAN = (
    (1, "define_objective", "Define objective and success criteria"),
    (2, "inspect_evidence", "Inspect evidence coverage"),
    (3, "validate_evidence", "Identify validation gaps and conflicts"),
    (4, "calculate_rti", "Calculate Research Trust Index"),
    (5, "build_consensus", "Build multi-agent consensus"),
    (6, "build_executive_brief", "Generate executive intelligence brief"),
    (7, "persist_snapshot", "Persist final executive snapshot"),
)


def create_mission(db: Session, owner_id: int, project: ResearchProject, payload: dict) -> Mission:
    mission = Mission(owner_id=owner_id, methodology_version=METHODOLOGY_VERSION, **payload)
    db.add(mission)
    db.flush()
    for order, key, title in STEP_PLAN:
        db.add(
            MissionStep(
                mission_id=mission.id,
                step_order=order,
                key=key,
                title=title,
                methodology_version=METHODOLOGY_VERSION,
                inputs={"project_id": project.id},
            )
        )
    db.commit()
    db.refresh(mission)
    return mission


def mission_steps(db: Session, mission_id: int) -> list[MissionStep]:
    return list(
        db.scalars(
            select(MissionStep)
            .where(MissionStep.mission_id == mission_id)
            .order_by(MissionStep.step_order, MissionStep.attempt)
        ).all()
    )


def _active_step(db: Session, mission: Mission) -> MissionStep | None:
    return db.scalar(
        select(MissionStep).where(
            MissionStep.mission_id == mission.id,
            MissionStep.step_order == mission.current_step_order + 1,
            MissionStep.attempt == 1,
        )
    )


def start_mission(db: Session, mission: Mission) -> Mission:
    if mission.status == "draft":
        mission.status = "running"
        mission.blocking_reason = None
        db.commit()
        db.refresh(mission)
    return mission


def _complete(step: MissionStep, outputs: dict) -> None:
    step.status = "completed"
    step.outputs = outputs
    step.blocking_reason = None
    step.completed_at = datetime.utcnow()


def _block(mission: Mission, step: MissionStep, reason: str, outputs: dict) -> None:
    step.status = "blocked"
    step.outputs = outputs
    step.blocking_reason = reason
    mission.status = "blocked"
    mission.blocking_reason = reason


def advance_mission(db: Session, mission: Mission, project: ResearchProject) -> Mission:
    if mission.status in {"completed", "cancelled"}:
        return mission
    if mission.status == "draft":
        start_mission(db, mission)
    if mission.status == "blocked":
        return mission

    step = _active_step(db, mission)
    if step is None:
        return mission
    step.status = "running"
    step.started_at = step.started_at or datetime.utcnow()

    evidence = list(
        db.scalars(
            select(EvidenceRecord).where(
                EvidenceRecord.owner_id == mission.owner_id,
                EvidenceRecord.project_id == mission.project_id,
            )
        ).all()
    )

    if step.key == "define_objective":
        _complete(
            step,
            {
                "objective": mission.objective,
                "success_criteria": mission.success_criteria,
                "project_id": mission.project_id,
            },
        )
    elif step.key == "inspect_evidence":
        outputs = {"evidence_count": len(evidence), "evidence_ids": sorted(item.id for item in evidence)}
        if not evidence:
            _block(mission, step, "At least one evidence record is required.", outputs)
        else:
            _complete(step, outputs)
    elif step.key == "validate_evidence":
        approved = [item for item in evidence if item.validation_status == "approved"]
        conflict_keys = {
            item.contradiction_key
            for item in evidence
            if item.contradiction_key and item.stance in {"supports", "contradicts"}
        }
        unresolved = [
            key
            for key in conflict_keys
            if {item.stance for item in evidence if item.contradiction_key == key}
            >= {"supports", "contradicts"}
        ]
        outputs = {
            "approved_evidence_ids": sorted(item.id for item in approved),
            "validation_ratio": round(len(approved) / len(evidence), 4) if evidence else 0.0,
            "unresolved_conflict_keys": sorted(unresolved),
        }
        if not approved:
            _block(mission, step, "At least one evidence record requires human approval.", outputs)
        elif unresolved:
            _block(mission, step, "Unresolved evidence conflicts require review.", outputs)
        else:
            _complete(step, outputs)
    elif step.key == "calculate_rti":
        _complete(step, calculate_project_rti(db, mission.owner_id, mission.project_id))
    elif step.key == "build_consensus":
        _complete(step, build_project_consensus(db, mission.owner_id, mission.project_id))
    elif step.key == "build_executive_brief":
        _complete(step, build_executive_brief(db, mission.owner_id, project))
    elif step.key == "persist_snapshot":
        snapshot, created = create_snapshot(db, mission.owner_id, project)
        mission.final_snapshot_id = snapshot.id
        _complete(step, {"snapshot_id": snapshot.id, "created": created})
        mission.status = "completed"
        mission.blocking_reason = None

    if step.status == "completed":
        mission.current_step_order = step.step_order
        if step.step_order < len(STEP_PLAN):
            mission.status = "running"
    db.commit()
    db.refresh(mission)
    return mission


def retry_blocked_step(db: Session, mission: Mission, step: MissionStep) -> Mission:
    if mission.status != "blocked" or step.status != "blocked":
        return mission
    step.status = "pending"
    step.outputs = {}
    step.blocking_reason = None
    step.started_at = None
    step.completed_at = None
    mission.status = "running"
    mission.blocking_reason = None
    db.commit()
    db.refresh(mission)
    return mission


def cancel_mission(db: Session, mission: Mission) -> Mission:
    if mission.status != "completed":
        mission.status = "cancelled"
        mission.blocking_reason = None
        db.commit()
        db.refresh(mission)
    return mission
