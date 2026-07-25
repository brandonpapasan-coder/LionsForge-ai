from datetime import datetime
from typing import Literal

from pydantic import BaseModel

EventCategory = Literal["claim", "evidence", "validation", "remediation_progress", "remediation_history"]
EventAction = Literal["created", "updated", "reviewed", "recorded"]
Authorship = Literal["user_authored", "human_judgment"]


class InvestigationProvenanceEvent(BaseModel):
    event_key: str
    category: EventCategory
    action: EventAction
    entity_type: str
    entity_id: int
    claim_id: int | None
    claim_statement: str | None
    authorship: Authorship
    summary: str
    occurred_at: datetime
    source_table: str
    source_record_id: int


class InvestigationProvenanceTimeline(BaseModel):
    contract_version: str = "1.0"
    investigation_id: int
    title: str
    status: Literal["empty", "active"]
    events: list[InvestigationProvenanceEvent]
    generated_from: Literal["stored_investigation_records"] = "stored_investigation_records"
    interpretation_notice: str = (
        "This read-only timeline reports chronology and source provenance from stored records. "
        "Chronology does not establish truth, confidence, quality, completion, or resolution."
    )
