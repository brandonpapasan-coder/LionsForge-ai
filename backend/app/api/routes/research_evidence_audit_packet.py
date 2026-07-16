import hashlib
import json
from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.evidence import EvidenceRecord, EvidenceReviewEvent
from app.models.research_project import ResearchProject
from app.models.user import User
from app.schemas.research_evidence_audit_packet import (
    AuditPacketComparisonSummary,
    AuditPacketEntryChange,
    AuditPacketProject,
    AuditPacketVerificationCheck,
    ResearchEvidenceAuditPacket,
    ResearchEvidenceAuditPacketComparison,
    ResearchEvidenceAuditPacketComparisonRequest,
    ResearchEvidenceAuditPacketVerification,
)
from app.schemas.research_evidence_provenance import ProvenanceLedgerEntry, ProvenanceLedgerSummary

router = APIRouter()
DISCLAIMER = "This packet records origin and review history. It does not certify that a claim is correct or complete."
VERIFICATION_DISCLAIMER = "Packet verification confirms structural consistency and integrity only. It does not certify that any claim is true."
COMPARISON_DISCLAIMER = "Packet comparison reports provenance and structural changes only. It does not certify claim truth, accuracy, or predictive value."
SUPPORTED_SCHEMA_VERSION = "1.0"


def _warning(record: EvidenceRecord) -> str | None:
    if not record.source_title.strip():
        return "Source title is missing."
    if record.source_type != "user" and not record.source_url:
        return "Source URL is missing for non-user evidence."
    return None


def _stable_packet_payload(packet: ResearchEvidenceAuditPacket) -> dict:
    return {
        "schema_version": packet.schema_version,
        "project": packet.project.model_dump(mode="json"),
        "summary": packet.summary.model_dump(mode="json"),
        "entries": [item.model_dump(mode="json") for item in packet.entries],
        "disclaimer": packet.disclaimer,
    }


def _packet_digest(packet: ResearchEvidenceAuditPacket) -> str:
    canonical = json.dumps(_stable_packet_payload(packet), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _verify_packet(packet: ResearchEvidenceAuditPacket) -> ResearchEvidenceAuditPacketVerification:
    computed_sha256 = _packet_digest(packet)
    integrity_matches = computed_sha256 == packet.content_sha256
    schema_version_supported = packet.schema_version == SUPPORTED_SCHEMA_VERSION
    ordered_entries = sorted(packet.entries, key=lambda item: (item.occurred_at, item.event_id))
    chronology_valid = [item.event_id for item in packet.entries] == [item.event_id for item in ordered_entries]
    evidence_ids = {item.evidence_id for item in packet.entries if item.event_type == "evidence_created"}
    broken_supersession_ids = sorted({
        item.supersedes_evidence_id
        for item in packet.entries
        if item.supersedes_evidence_id is not None and item.supersedes_evidence_id not in evidence_ids
    })
    supersession_references_valid = not broken_supersession_ids
    checks = [
        AuditPacketVerificationCheck(code="schema_version", passed=schema_version_supported, message="Schema version is supported." if schema_version_supported else f"Unsupported schema version: {packet.schema_version}."),
        AuditPacketVerificationCheck(code="integrity_sha256", passed=integrity_matches, message="Integrity digest matches the canonical packet content." if integrity_matches else "Integrity digest does not match the canonical packet content."),
        AuditPacketVerificationCheck(code="event_chronology", passed=chronology_valid, message="Events are in deterministic chronological order." if chronology_valid else "Events are not in deterministic chronological order."),
        AuditPacketVerificationCheck(code="supersession_references", passed=supersession_references_valid, message="Supersession references resolve within the packet." if supersession_references_valid else f"Missing superseded evidence IDs: {broken_supersession_ids}."),
    ]
    return ResearchEvidenceAuditPacketVerification(
        valid=all(check.passed for check in checks),
        schema_version_supported=schema_version_supported,
        integrity_matches=integrity_matches,
        chronology_valid=chronology_valid,
        supersession_references_valid=supersession_references_valid,
        computed_sha256=computed_sha256,
        checks=checks,
        disclaimer=VERIFICATION_DISCLAIMER,
    )


def _changed_fields(baseline: ProvenanceLedgerEntry, current: ProvenanceLedgerEntry) -> list[str]:
    before = baseline.model_dump(mode="json")
    after = current.model_dump(mode="json")
    return sorted(key for key in before if key != "event_id" and before[key] != after[key])


@router.get("/projects/{project_id}/audit-packet", response_model=ResearchEvidenceAuditPacket)
def get_audit_packet(project_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ResearchEvidenceAuditPacket:
    project = db.scalar(select(ResearchProject).where(ResearchProject.id == project_id, ResearchProject.owner_id == current_user.id))
    if project is None:
        raise HTTPException(status_code=404, detail="Research project not found")
    records = list(db.scalars(select(EvidenceRecord).where(EvidenceRecord.owner_id == current_user.id, EvidenceRecord.project_id == project.id).order_by(EvidenceRecord.created_at, EvidenceRecord.id)).all())
    by_id = {record.id: record for record in records}
    reviews = [] if not by_id else list(db.scalars(select(EvidenceReviewEvent).where(EvidenceReviewEvent.owner_id == current_user.id, EvidenceReviewEvent.evidence_id.in_(list(by_id))).order_by(EvidenceReviewEvent.created_at, EvidenceReviewEvent.id)).all())
    entries: list[ProvenanceLedgerEntry] = []
    superseded = 0
    missing = 0
    for record in records:
        warning = _warning(record)
        missing += int(warning is not None)
        supersedes_id = record.provenance.get("supersedes_evidence_id") if record.provenance else None
        entries.append(ProvenanceLedgerEntry(event_id=f"evidence:{record.id}", event_type="evidence_created", evidence_id=record.id, project_id=record.project_id, source_title=record.source_title, source_type=record.source_type, claim=record.claim, validation_status=record.validation_status, contradiction_key=record.contradiction_key, supersedes_evidence_id=supersedes_id, warning=warning, occurred_at=record.created_at))
        if supersedes_id is not None:
            superseded += 1
            entries.append(ProvenanceLedgerEntry(event_id=f"supersession:{record.id}:{supersedes_id}", event_type="claim_superseded", evidence_id=record.id, project_id=record.project_id, source_title=record.source_title, source_type=record.source_type, claim=record.claim, validation_status=record.validation_status, contradiction_key=record.contradiction_key, supersedes_evidence_id=supersedes_id, warning=None if supersedes_id in by_id else "Superseded evidence is outside this packet.", occurred_at=record.created_at))
    for review in reviews:
        record = by_id[review.evidence_id]
        entries.append(ProvenanceLedgerEntry(event_id=f"review:{review.id}", event_type="review_recorded", evidence_id=record.id, project_id=record.project_id, source_title=record.source_title, source_type=record.source_type, claim=record.claim, validation_status=review.validation_status, contradiction_key=record.contradiction_key, reviewer_notes=review.reviewer_notes, warning=_warning(record), occurred_at=review.created_at))
    entries.sort(key=lambda item: (item.occurred_at, item.event_id))
    counts = Counter(record.contradiction_key for record in records if record.contradiction_key and record.validation_status not in {"approved", "rejected"})
    summary = ProvenanceLedgerSummary(total_evidence=len(records), total_events=len(entries), unresolved_contradictions=sum(1 for count in counts.values() if count > 1), superseded_claims=superseded, missing_source_metadata=missing)
    project_snapshot = AuditPacketProject.model_validate(project, from_attributes=True)
    packet = ResearchEvidenceAuditPacket(generated_at=datetime.utcnow(), project=project_snapshot, summary=summary, entries=entries, disclaimer=DISCLAIMER, content_sha256="")
    packet.content_sha256 = _packet_digest(packet)
    return packet


@router.post("/audit-packet/verify", response_model=ResearchEvidenceAuditPacketVerification)
def verify_audit_packet(packet: ResearchEvidenceAuditPacket, current_user: User = Depends(get_current_user)) -> ResearchEvidenceAuditPacketVerification:
    del current_user
    return _verify_packet(packet)


@router.post("/audit-packet/compare", response_model=ResearchEvidenceAuditPacketComparison)
def compare_audit_packets(request: ResearchEvidenceAuditPacketComparisonRequest, current_user: User = Depends(get_current_user)) -> ResearchEvidenceAuditPacketComparison:
    del current_user
    baseline_verification = _verify_packet(request.baseline)
    current_verification = _verify_packet(request.current)
    comparable = baseline_verification.valid and current_verification.valid and request.baseline.schema_version == request.current.schema_version

    baseline_entries = {entry.event_id: entry for entry in request.baseline.entries}
    current_entries = {entry.event_id: entry for entry in request.current.entries}
    changes: list[AuditPacketEntryChange] = []
    counts = Counter()
    for event_id in sorted(set(baseline_entries) | set(current_entries)):
        before = baseline_entries.get(event_id)
        after = current_entries.get(event_id)
        if before is None and after is not None:
            classification, fields, explanation = "added", [], f"{after.event_type} was added to the current packet."
        elif before is not None and after is None:
            classification, fields, explanation = "removed", [], f"{before.event_type} is no longer present in the current packet."
        elif before is not None and after is not None:
            fields = _changed_fields(before, after)
            classification = "changed" if fields else "unchanged"
            explanation = f"Changed fields: {', '.join(fields)}." if fields else "Event is unchanged."
        else:
            continue
        counts[classification] += 1
        reference = after or before
        changes.append(AuditPacketEntryChange(event_id=event_id, classification=classification, event_type=reference.event_type, evidence_id=reference.evidence_id, changed_fields=fields, explanation=explanation, baseline=before, current=after))

    project_before = request.baseline.project.model_dump(mode="json")
    project_after = request.current.project.model_dump(mode="json")
    project_changes = sorted(key for key in project_before if project_before[key] != project_after[key])
    summary_before = request.baseline.summary.model_dump(mode="json")
    summary_after = request.current.summary.model_dump(mode="json")
    summary_changes = sorted(key for key in summary_before if summary_before[key] != summary_after[key])

    return ResearchEvidenceAuditPacketComparison(
        comparable=comparable,
        baseline_verification=baseline_verification,
        current_verification=current_verification,
        summary=AuditPacketComparisonSummary(added=counts["added"], removed=counts["removed"], changed=counts["changed"], unchanged=counts["unchanged"], project_changed=bool(project_changes), summary_changed=bool(summary_changes)),
        changes=changes,
        project_changes=project_changes,
        summary_changes=summary_changes,
        disclaimer=COMPARISON_DISCLAIMER,
    )
