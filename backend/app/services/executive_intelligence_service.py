from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import EvidenceRecord
from app.models.research_project import ResearchProject
from app.services.multi_agent_consensus_service import build_project_consensus


METHODOLOGY_VERSION = "executive-brief-v1"


def _severity(conflict_count: int, contradiction_count: int) -> str:
    total = conflict_count + contradiction_count
    if total >= 5:
        return "critical"
    if total >= 3:
        return "high"
    if total >= 1:
        return "medium"
    return "low"


def build_executive_brief(
    db: Session,
    owner_id: int,
    project: ResearchProject,
) -> dict:
    evidence = list(
        db.scalars(
            select(EvidenceRecord).where(
                EvidenceRecord.owner_id == owner_id,
                EvidenceRecord.project_id == project.id,
            )
        ).all()
    )
    consensus = build_project_consensus(db, owner_id, project.id)

    approved = [item for item in evidence if item.validation_status == "approved"]
    contradicted = [item for item in evidence if item.stance == "contradicts"]
    source_ids = sorted(item.id for item in evidence)
    validation_coverage = (len(approved) / len(evidence) * 100) if evidence else 0.0
    conflict_penalty = min(
        100.0,
        (len(consensus["conflicts"]) * 20.0) + (len(contradicted) * 5.0),
    )

    breakdown = {
        "evidence_quality": round(consensus["research_trust_index"], 2),
        "consensus_strength": round(consensus["agreement_score"], 2),
        "validation_coverage": round(validation_coverage, 2),
        "conflict_penalty": round(conflict_penalty, 2),
    }
    readiness = round(
        max(
            0.0,
            min(
                100.0,
                (breakdown["evidence_quality"] * 0.4)
                + (breakdown["consensus_strength"] * 0.3)
                + (breakdown["validation_coverage"] * 0.3)
                - (breakdown["conflict_penalty"] * 0.25),
            ),
        ),
        2,
    )

    if not evidence:
        recommendation = "insufficient_evidence"
    elif consensus["conflicts"] or readiness < 60:
        recommendation = "investigate"
    elif readiness >= 80 and consensus["consensus_status"] == "strong_agreement":
        recommendation = "go"
    else:
        recommendation = "hold"

    verified_facts = [
        {
            "statement": item.claim,
            "evidence_ids": [item.id],
            "verified": True,
            "confidence": item.confidence_score,
        }
        for item in approved
    ]
    provisional = [
        item["conclusion"]
        for item in consensus["findings"]
        if item["confidence"] < 0.8 or recommendation != "go"
    ]
    assumptions = list(
        dict.fromkeys(
            assumption
            for finding in consensus["findings"]
            for assumption in finding["assumptions"]
        )
    )
    minority_findings = [
        item.claim
        for item in contradicted
    ]

    risks = []
    if consensus["conflicts"] or contradicted:
        risks.append(
            {
                "category": "evidence_conflict",
                "summary": (
                    f"{len(consensus['conflicts'])} unresolved conflict groups and "
                    f"{len(contradicted)} contradicting evidence records remain."
                ),
                "severity": _severity(len(consensus["conflicts"]), len(contradicted)),
                "evidence_ids": sorted(item.id for item in contradicted),
            }
        )
    if validation_coverage < 75:
        risks.append(
            {
                "category": "validation_gap",
                "summary": "Human validation coverage is below the 75% decision-readiness target.",
                "severity": "high" if validation_coverage < 25 else "medium",
                "evidence_ids": source_ids,
            }
        )

    executive_summary = (
        f"{project.title}: recommendation is {recommendation}. "
        f"Decision readiness is {readiness:.2f}/100, research trust is "
        f"{consensus['research_trust_index']:.2f}/100, and consensus status is "
        f"{consensus['consensus_status']}."
    )

    return {
        "project_id": project.id,
        "project_title": project.title,
        "objective": project.objective,
        "recommendation": recommendation,
        "decision_readiness_score": readiness,
        "readiness_breakdown": breakdown,
        "research_trust_index": consensus["research_trust_index"],
        "consensus_status": consensus["consensus_status"],
        "overall_confidence": consensus["overall_confidence"],
        "executive_summary": executive_summary,
        "verified_facts": verified_facts,
        "provisional_conclusions": list(dict.fromkeys(provisional)),
        "assumptions": assumptions,
        "risks": risks,
        "minority_findings": minority_findings,
        "unresolved_questions": consensus["unresolved_questions"],
        "recommended_actions": consensus["recommended_actions"],
        "source_evidence_ids": source_ids,
        "methodology_version": METHODOLOGY_VERSION,
    }
