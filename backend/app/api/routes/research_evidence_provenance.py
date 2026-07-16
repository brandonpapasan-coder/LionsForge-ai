from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.evidence import EvidenceRecord, EvidenceReviewEvent
from app.models.user import User
from app.schemas.research_evidence_provenance import (
    ProvenanceLedgerEntry,
    ProvenanceLedgerSummary,
    ResearchEvidenceProvenanceLedger,
)

router = APIRouter()

DISCLAIMER = (
    "Provenance records trace origin and revision history. They do not verify that a claim is true, "
    "accurate, complete, or suitable for financial decisions."
)


def _source_warning(evidence: EvidenceRecord) -> str | None:
    if not evidence.source_title.strip():
        return "Source title is missing."
    if evidence.source_type != "user" and not evidence.source_url:
        return "Source URL is missing for non-user evidence."
    return None


@router.get("/ledger", response_model=ResearchEvidenceProvenanceLedger)
def get_provenance_ledger(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResearchEvidenceProvenanceLedger:
    evidence_records = list(
        db.scalars(
            select(EvidenceRecord)
            .where(EvidenceRecord.owner_id == current_user.id)
            .order_by(EvidenceRecord.created_at, EvidenceRecord.id)
        ).all()
    )
    evidence_by_id = {record.id: record for record in evidence_records}
    review_events = list(
        db.scalars(
            select(EvidenceReviewEvent)
            .where(EvidenceReviewEvent.owner_id == current_user.id)
            .order_by(EvidenceReviewEvent.created_at, EvidenceReviewEvent.id)
        ).all()
    )

    entries: list[ProvenanceLedgerEntry] = []
    superseded_claims = 0
    missing_source_metadata = 0

    for evidence in evidence_records:
        warning = _source_warning(evidence)
        if warning:
            missing_source_metadata += 1
        supersedes_id = evidence.provenance.get("supersedes_evidence_id") if evidence.provenance else None
        entries.append(
            ProvenanceLedgerEntry(
                event_id=f"evidence:{evidence.id}",
                event_type="evidence_created",
                evidence_id=evidence.id,
                project_id=evidence.project_id,
                source_title=evidence.source_title,
                source_type=evidence.source_type,
                claim=evidence.claim,
                validation_status=evidence.validation_status,
                contradiction_key=evidence.contradiction_key,
                supersedes_evidence_id=supersedes_id,
                warning=warning,
                occurred_at=evidence.created_at,
            )
        )
        if supersedes_id is not None:
            superseded_claims += 1
            entries.append(
                ProvenanceLedgerEntry(
                    event_id=f"supersession:{evidence.id}:{supersedes_id}",
                    event_type="claim_superseded",
                    evidence_id=evidence.id,
                    project_id=evidence.project_id,
                    source_title=evidence.source_title,
                    source_type=evidence.source_type,
                    claim=evidence.claim,
                    validation_status=evidence.validation_status,
                    contradiction_key=evidence.contradiction_key,
                    supersedes_evidence_id=supersedes_id,
                    warning=None if supersedes_id in evidence_by_id else "Superseded evidence is not available in this ledger.",
                    occurred_at=evidence.created_at,
                )
            )

    for review in review_events:
        evidence = evidence_by_id.get(review.evidence_id)
        if evidence is None:
            continue
        entries.append(
            ProvenanceLedgerEntry(
                event_id=f"review:{review.id}",
                event_type="review_recorded",
                evidence_id=evidence.id,
                project_id=evidence.project_id,
                source_title=evidence.source_title,
                source_type=evidence.source_type,
                claim=evidence.claim,
                validation_status=review.validation_status,
                contradiction_key=evidence.contradiction_key,
                reviewer_notes=review.reviewer_notes,
                warning=_source_warning(evidence),
                occurred_at=review.created_at,
            )
        )

    entries.sort(key=lambda entry: (entry.occurred_at, entry.event_id))
    contradiction_counts = Counter(
        record.contradiction_key
        for record in evidence_records
        if record.contradiction_key and record.validation_status not in {"approved", "rejected"}
    )
    unresolved_contradictions = sum(1 for count in contradiction_counts.values() if count > 1)

    return ResearchEvidenceProvenanceLedger(
        summary=ProvenanceLedgerSummary(
            total_evidence=len(evidence_records),
            total_events=len(entries),
            unresolved_contradictions=unresolved_contradictions,
            superseded_claims=superseded_claims,
            missing_source_metadata=missing_source_metadata,
        ),
        entries=entries,
        disclaimer=DISCLAIMER,
    )
