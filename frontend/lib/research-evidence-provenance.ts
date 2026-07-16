export type ProvenanceLedgerEntry = {
  event_id: string;
  event_type: string;
  evidence_id: number;
  project_id: number | null;
  source_title: string;
  source_type: string;
  claim: string;
  validation_status: string;
  contradiction_key: string | null;
  supersedes_evidence_id: number | null;
  reviewer_notes: string | null;
  warning: string | null;
  occurred_at: string;
};

export type ProvenanceLedgerSummary = {
  total_evidence: number;
  total_events: number;
  unresolved_contradictions: number;
  superseded_claims: number;
  missing_source_metadata: number;
};

export type ResearchEvidenceProvenanceLedger = {
  summary: ProvenanceLedgerSummary;
  entries: ProvenanceLedgerEntry[];
  disclaimer: string;
};
