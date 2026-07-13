from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import EvidenceRecord
from app.services.research_trust_index_service import calculate_project_rti


def _finding(
    agent: str,
    conclusion: str,
    confidence: float,
    evidence_ids: list[int],
    assumptions: list[str] | None = None,
    limitations: list[str] | None = None,
    recommended_actions: list[str] | None = None,
) -> dict:
    return {
        "agent": agent,
        "conclusion": conclusion,
        "confidence": round(max(0.0, min(confidence, 1.0)), 4),
        "evidence_ids": evidence_ids,
        "assumptions": assumptions or [],
        "limitations": limitations or [],
        "recommended_actions": recommended_actions or [],
    }


def build_project_consensus(db: Session, owner_id: int, project_id: int) -> dict:
    evidence = list(
        db.scalars(
            select(EvidenceRecord).where(
                EvidenceRecord.owner_id == owner_id,
                EvidenceRecord.project_id == project_id,
            )
        ).all()
    )
    rti = calculate_project_rti(db, owner_id, project_id)
    supporting = [item for item in evidence if item.stance == "supports"]
    contradicting = [item for item in evidence if item.stance == "contradicts"]
    approved = [item for item in evidence if item.validation_status == "approved"]

    conflict_map: dict[str, dict[str, list[int]]] = defaultdict(lambda: {"supports": [], "contradicts": []})
    for item in evidence:
        if item.contradiction_key and item.stance in {"supports", "contradicts"}:
            conflict_map[item.contradiction_key][item.stance].append(item.id)

    conflicts = [
        {
            "key": key,
            "supporting_evidence_ids": sides["supports"],
            "contradicting_evidence_ids": sides["contradicts"],
            "summary": f"Evidence conflict remains unresolved for '{key}'.",
        }
        for key, sides in conflict_map.items()
        if sides["supports"] and sides["contradicts"]
    ]

    evidence_confidence = (
        sum(item.confidence_score for item in evidence) / len(evidence) if evidence else 0.0
    )
    validation_ratio = len(approved) / len(evidence) if evidence else 0.0
    support_ratio = len(supporting) / len(evidence) if evidence else 0.0
    contradiction_ratio = len(contradicting) / len(evidence) if evidence else 0.0

    findings = [
        _finding(
            "research",
            f"The project contains {len(evidence)} evidence records covering the research objective.",
            min(len(evidence) / 8, 1.0),
            [item.id for item in evidence],
            limitations=[] if len(evidence) >= 8 else ["Evidence coverage is below the MVP completeness target."],
            recommended_actions=[] if len(evidence) >= 8 else ["Expand the evidence base."],
        ),
        _finding(
            "evidence",
            f"Average evidence confidence is {evidence_confidence:.2f}; {len(approved)} records are human approved.",
            (evidence_confidence * 0.75) + (validation_ratio * 0.25),
            [item.id for item in evidence],
            limitations=[] if validation_ratio >= 0.75 else ["Most evidence has not completed human validation."],
            recommended_actions=[] if validation_ratio >= 0.75 else ["Review high-impact evidence records."],
        ),
        _finding(
            "verification",
            f"There are {len(conflicts)} unresolved conflict groups and {len(contradicting)} contradicting records.",
            max(1.0 - contradiction_ratio - (len(conflicts) * 0.1), 0.0),
            [item.id for item in contradicting],
            limitations=[item["summary"] for item in conflicts],
            recommended_actions=["Resolve contradictory claims with independent primary sources."] if conflicts else [],
        ),
    ]

    confidence_values = [item["confidence"] for item in findings]
    mean_confidence = sum(confidence_values) / len(confidence_values)
    spread = max(confidence_values) - min(confidence_values)
    agreement_score = round(max(0.0, (1.0 - spread) * 100), 2)
    overall_confidence = round((mean_confidence * 0.6) + ((rti["overall_score"] / 100) * 0.4), 4)

    if not evidence:
        consensus_status = "insufficient_evidence"
        final_conclusion = "No consensus can be formed because the project has no evidence."
    elif conflicts or agreement_score < 65:
        consensus_status = "split"
        final_conclusion = "The available evidence supports only a provisional conclusion because meaningful conflicts remain."
    elif overall_confidence >= 0.8 and support_ratio >= 0.5:
        consensus_status = "strong_agreement"
        final_conclusion = "The specialist agents reached strong evidence-backed agreement."
    else:
        consensus_status = "moderate_agreement"
        final_conclusion = "The specialist agents reached moderate agreement with remaining uncertainty."

    unresolved_questions = [conflict["summary"] for conflict in conflicts]
    if len(evidence) < 8:
        unresolved_questions.append("Does additional evidence materially change the conclusion?")
    if validation_ratio < 0.75:
        unresolved_questions.append("Will human review confirm the highest-impact evidence?")

    actions: list[str] = []
    for finding in findings:
        actions.extend(finding["recommended_actions"])
    actions.extend(rti["recommended_actions"])

    return {
        "project_id": project_id,
        "consensus_status": consensus_status,
        "agreement_score": agreement_score,
        "overall_confidence": overall_confidence,
        "research_trust_index": rti["overall_score"],
        "final_conclusion": final_conclusion,
        "findings": findings,
        "conflicts": conflicts,
        "unresolved_questions": list(dict.fromkeys(unresolved_questions)),
        "recommended_actions": list(dict.fromkeys(actions)),
        "methodology_version": "consensus-v1",
    }
