from collections import Counter
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import EvidenceRecord

RTI_WEIGHTS = {
    "evidence_quality": 0.25,
    "source_diversity": 0.15,
    "corroboration": 0.20,
    "freshness": 0.10,
    "human_validation": 0.15,
    "completeness": 0.15,
}


def _clamp(value: float) -> float:
    return round(max(0.0, min(value, 100.0)), 2)


def _source_identity(record: EvidenceRecord) -> str:
    if record.publisher:
        return record.publisher.casefold().strip()
    if record.source_url:
        return urlparse(record.source_url).netloc.casefold()
    return record.source_title.casefold().strip()


def _component(key: str, label: str, score: float, explanation: str, recommendations: list[str]) -> dict:
    weight = RTI_WEIGHTS[key]
    return {
        "key": key,
        "label": label,
        "score": _clamp(score),
        "weight": weight,
        "weighted_score": round(_clamp(score) * weight, 2),
        "explanation": explanation,
        "recommendations": recommendations,
    }


def calculate_project_rti(db: Session, owner_id: int, project_id: int) -> dict:
    evidence = list(
        db.scalars(
            select(EvidenceRecord).where(
                EvidenceRecord.owner_id == owner_id,
                EvidenceRecord.project_id == project_id,
            )
        ).all()
    )

    evidence_count = len(evidence)
    supporting = [item for item in evidence if item.stance == "supports"]
    contradicting = [item for item in evidence if item.stance == "contradicts"]
    approved = [item for item in evidence if item.validation_status == "approved"]
    unique_sources = {_source_identity(item) for item in evidence}

    conflict_keys: dict[str, set[str]] = {}
    for item in evidence:
        if item.contradiction_key:
            conflict_keys.setdefault(item.contradiction_key, set()).add(item.stance)
    conflict_count = sum(1 for stances in conflict_keys.values() if {"supports", "contradicts"}.issubset(stances))

    avg_confidence = sum(item.confidence_score for item in evidence) / evidence_count if evidence else 0.0
    avg_freshness = sum(item.freshness_score for item in evidence) / evidence_count if evidence else 0.0
    source_diversity = min(len(unique_sources) / 5, 1.0) if evidence else 0.0
    validation_ratio = len(approved) / evidence_count if evidence else 0.0
    completeness = min(evidence_count / 8, 1.0)

    if supporting:
        support_sources = {_source_identity(item) for item in supporting}
        corroboration = min(len(support_sources) / 3, 1.0)
    else:
        corroboration = 0.0
    if conflict_count:
        corroboration = max(corroboration - min(conflict_count * 0.15, 0.45), 0.0)

    components = [
        _component(
            "evidence_quality",
            "Evidence Quality",
            avg_confidence * 100,
            f"Average evidence confidence is {avg_confidence:.2f} across {evidence_count} records.",
            [] if avg_confidence >= 0.75 else ["Add higher-authority primary or official sources."],
        ),
        _component(
            "source_diversity",
            "Source Diversity",
            source_diversity * 100,
            f"Research uses {len(unique_sources)} distinct source identities.",
            [] if source_diversity >= 0.8 else ["Add independent sources from different publishers or domains."],
        ),
        _component(
            "corroboration",
            "Independent Corroboration",
            corroboration * 100,
            f"Supporting evidence spans {len({_source_identity(item) for item in supporting})} independent sources; {conflict_count} conflict groups remain.",
            [] if corroboration >= 0.75 else ["Collect additional independent support and resolve conflicting claims."],
        ),
        _component(
            "freshness",
            "Freshness",
            avg_freshness * 100,
            f"Average evidence freshness is {avg_freshness:.2f}.",
            [] if avg_freshness >= 0.7 else ["Refresh older or undated evidence."],
        ),
        _component(
            "human_validation",
            "Human Validation",
            validation_ratio * 100,
            f"{len(approved)} of {evidence_count} evidence records are approved.",
            [] if validation_ratio >= 0.75 else ["Review and approve high-impact evidence records."],
        ),
        _component(
            "completeness",
            "Research Completeness",
            completeness * 100,
            f"The project contains {evidence_count} evidence records; the MVP completeness target is 8.",
            [] if completeness >= 1.0 else ["Expand evidence coverage before relying on the final recommendation."],
        ),
    ]

    overall_score = round(sum(item["weighted_score"] for item in components), 2)
    if overall_score >= 85:
        confidence_level = "high"
    elif overall_score >= 65:
        confidence_level = "moderate"
    elif overall_score >= 40:
        confidence_level = "low"
    else:
        confidence_level = "insufficient"

    strengths = [item["label"] for item in components if item["score"] >= 80]
    limitations = [item["explanation"] for item in components if item["score"] < 60]
    if conflict_count:
        limitations.append(f"{conflict_count} unresolved evidence conflict groups reduce trust.")

    actions: list[str] = []
    for item in components:
        actions.extend(item["recommendations"])
    actions = list(dict.fromkeys(actions))

    return {
        "project_id": project_id,
        "overall_score": overall_score,
        "confidence_level": confidence_level,
        "evidence_count": evidence_count,
        "supporting_count": len(supporting),
        "contradicting_count": len(contradicting),
        "approved_count": len(approved),
        "conflict_count": conflict_count,
        "components": components,
        "strengths": strengths,
        "limitations": limitations,
        "recommended_actions": actions,
        "methodology_version": "rti-v1",
    }
