import hashlib
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.evidence import EvidenceRecord

SOURCE_WEIGHTS = {
    "official": 0.95,
    "primary": 0.9,
    "expert": 0.8,
    "secondary": 0.65,
    "user": 0.45,
}


def _normalize_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def evidence_fingerprint(source_url: str | None, claim: str, excerpt: str) -> str:
    raw = "|".join((_normalize_text(source_url or ""), _normalize_text(claim), _normalize_text(excerpt)))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def calculate_freshness(published_at: datetime | None, now: datetime | None = None) -> float:
    if published_at is None:
        return 0.5
    current = now or datetime.now(timezone.utc)
    published = published_at if published_at.tzinfo else published_at.replace(tzinfo=timezone.utc)
    age_days = max((current - published).days, 0)
    if age_days <= 30:
        return 1.0
    if age_days <= 180:
        return 0.85
    if age_days <= 365:
        return 0.7
    if age_days <= 1095:
        return 0.5
    return 0.3


def calculate_credibility(source_type: str, author: str | None, publisher: str | None, source_url: str | None) -> float:
    score = SOURCE_WEIGHTS.get(source_type, 0.5)
    if author:
        score += 0.03
    if publisher:
        score += 0.03
    if source_url and source_url.startswith("https://"):
        score += 0.02
    return round(min(score, 1.0), 4)


def calculate_confidence(credibility: float, freshness: float) -> float:
    return round((credibility * 0.7) + (freshness * 0.3), 4)


def build_evidence_record(owner_id: int, payload: dict) -> EvidenceRecord:
    source_url = str(payload.get("source_url")) if payload.get("source_url") else None
    credibility = calculate_credibility(
        payload["source_type"], payload.get("author"), payload.get("publisher"), source_url
    )
    freshness = calculate_freshness(payload.get("published_at"))
    return EvidenceRecord(
        owner_id=owner_id,
        source_url=source_url,
        fingerprint=evidence_fingerprint(source_url, payload["claim"], payload["excerpt"]),
        credibility_score=credibility,
        freshness_score=freshness,
        confidence_score=calculate_confidence(credibility, freshness),
        **{key: value for key, value in payload.items() if key != "source_url"},
    )


def find_duplicate(db: Session, owner_id: int, fingerprint: str) -> EvidenceRecord | None:
    return db.scalar(
        select(EvidenceRecord).where(
            EvidenceRecord.owner_id == owner_id,
            EvidenceRecord.fingerprint == fingerprint,
        )
    )


def conflict_groups(db: Session, owner_id: int, project_id: int | None = None) -> dict[str, list[EvidenceRecord]]:
    statement = select(EvidenceRecord).where(
        EvidenceRecord.owner_id == owner_id,
        EvidenceRecord.contradiction_key.is_not(None),
    )
    if project_id is not None:
        statement = statement.where(EvidenceRecord.project_id == project_id)
    grouped: dict[str, list[EvidenceRecord]] = {}
    for item in db.scalars(statement).all():
        grouped.setdefault(item.contradiction_key or "", []).append(item)
    return {
        key: records
        for key, records in grouped.items()
        if any(record.stance == "supports" for record in records)
        and any(record.stance == "contradicts" for record in records)
    }
