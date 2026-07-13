import hashlib
import json

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.executive_brief_snapshot import ExecutiveBriefSnapshot
from app.models.research_project import ResearchProject
from app.services.executive_intelligence_service import build_executive_brief


def snapshot_fingerprint(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def create_snapshot(
    db: Session,
    owner_id: int,
    project: ResearchProject,
    force: bool = False,
) -> tuple[ExecutiveBriefSnapshot, bool]:
    payload = build_executive_brief(db, owner_id, project)
    fingerprint = snapshot_fingerprint(payload)
    existing = db.scalar(
        select(ExecutiveBriefSnapshot).where(
            ExecutiveBriefSnapshot.owner_id == owner_id,
            ExecutiveBriefSnapshot.project_id == project.id,
            ExecutiveBriefSnapshot.fingerprint == fingerprint,
        )
    )
    if existing is not None and not force:
        return existing, False

    if existing is not None and force:
        fingerprint = hashlib.sha256(
            f"{fingerprint}:{existing.id}:{existing.created_at.isoformat()}".encode("utf-8")
        ).hexdigest()

    snapshot = ExecutiveBriefSnapshot(
        owner_id=owner_id,
        project_id=project.id,
        fingerprint=fingerprint,
        recommendation=payload["recommendation"],
        decision_readiness_score=payload["decision_readiness_score"],
        research_trust_index=payload["research_trust_index"],
        consensus_status=payload["consensus_status"],
        overall_confidence=payload["overall_confidence"],
        methodology_version=payload["methodology_version"],
        source_evidence_ids=payload["source_evidence_ids"],
        payload=payload,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot, True


def list_project_snapshots(db: Session, owner_id: int, project_id: int) -> list[ExecutiveBriefSnapshot]:
    return list(
        db.scalars(
            select(ExecutiveBriefSnapshot)
            .where(
                ExecutiveBriefSnapshot.owner_id == owner_id,
                ExecutiveBriefSnapshot.project_id == project_id,
            )
            .order_by(desc(ExecutiveBriefSnapshot.created_at), desc(ExecutiveBriefSnapshot.id))
        ).all()
    )


def compare_snapshots(left: ExecutiveBriefSnapshot, right: ExecutiveBriefSnapshot) -> dict:
    left_payload = left.payload
    right_payload = right.payload
    return {
        "left_snapshot_id": left.id,
        "right_snapshot_id": right.id,
        "recommendation_changed": left.recommendation != right.recommendation,
        "recommendation": {"left": left.recommendation, "right": right.recommendation},
        "decision_readiness_delta": round(right.decision_readiness_score - left.decision_readiness_score, 2),
        "research_trust_index_delta": round(right.research_trust_index - left.research_trust_index, 2),
        "overall_confidence_delta": round(right.overall_confidence - left.overall_confidence, 4),
        "consensus_status": {"left": left.consensus_status, "right": right.consensus_status},
        "evidence_added": sorted(set(right.source_evidence_ids) - set(left.source_evidence_ids)),
        "evidence_removed": sorted(set(left.source_evidence_ids) - set(right.source_evidence_ids)),
        "risks_added": [item for item in right_payload.get("risks", []) if item not in left_payload.get("risks", [])],
        "risks_removed": [item for item in left_payload.get("risks", []) if item not in right_payload.get("risks", [])],
        "unresolved_questions_added": sorted(set(right_payload.get("unresolved_questions", [])) - set(left_payload.get("unresolved_questions", []))),
        "unresolved_questions_resolved": sorted(set(left_payload.get("unresolved_questions", [])) - set(right_payload.get("unresolved_questions", []))),
        "recommended_actions_added": sorted(set(right_payload.get("recommended_actions", [])) - set(left_payload.get("recommended_actions", []))),
        "recommended_actions_removed": sorted(set(left_payload.get("recommended_actions", [])) - set(right_payload.get("recommended_actions", []))),
    }
