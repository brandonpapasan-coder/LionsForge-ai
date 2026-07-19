export type InvestigationStatus = "open" | "in_review" | "validated" | "archived";
export type EvidenceType = "primary" | "secondary" | "dataset" | "expert" | "other";
export type EvidenceRelationship = "supports" | "contradicts" | "neutral";

export type Investigation = {
  id: number;
  title: string;
  research_question: string;
  status: InvestigationStatus;
  created_at: string;
  updated_at: string;
};

export type InvestigationClaim = {
  id: number;
  investigation_id: number;
  statement: string;
  created_at: string;
  updated_at: string;
};

export type ClaimEvidence = {
  id: number;
  claim_id: number;
  source_title: string;
  source_url: string;
  evidence_type: EvidenceType;
  relationship: EvidenceRelationship;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type InvestigationCreate = {
  title: string;
  research_question: string;
};

export type InvestigationUpdate = Partial<InvestigationCreate> & {
  status?: InvestigationStatus;
};
