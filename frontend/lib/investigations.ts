export type InvestigationStatus = "open" | "in_review" | "validated" | "archived";
export type EvidenceType = "primary" | "secondary" | "dataset" | "expert" | "other";
export type EvidenceRelationship = "supports" | "contradicts" | "neutral";
export type AssessmentLevel = "low" | "medium" | "high";
export type ValidationStatus = "unreviewed" | "supported" | "mixed" | "contradicted" | "insufficient";

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
  confidence_level: AssessmentLevel | null;
  confidence_rationale: string | null;
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
  credibility_rating: AssessmentLevel | null;
  credibility_rationale: string | null;
  created_at: string;
  updated_at: string;
};

export type ClaimValidationJudgment = {
  id: number;
  claim_id: number;
  reviewer_id: number;
  validation_status: ValidationStatus;
  confidence_level: AssessmentLevel;
  rationale: string;
  unresolved_questions: string | null;
  reviewed_at: string;
  is_stale: boolean;
};

export type ClaimValidationJudgmentCreate = {
  validation_status: ValidationStatus;
  confidence_level: AssessmentLevel;
  rationale: string;
  unresolved_questions?: string | null;
};

export type ClaimValidationSummary = {
  claim_id: number;
  confidence_level: AssessmentLevel | null;
  supporting_count: number;
  contradicting_count: number;
  neutral_count: number;
  assessed_evidence_count: number;
  total_evidence_count: number;
  has_unresolved_contradiction: boolean;
};

export type InvestigationValidationSummary = {
  investigation_id: number;
  claim_count: number;
  assessed_claim_count: number;
  low_confidence_count: number;
  medium_confidence_count: number;
  high_confidence_count: number;
  unresolved_contradiction_count: number;
  claims: ClaimValidationSummary[];
};

export type InvestigationCreate = {
  title: string;
  research_question: string;
};

export type InvestigationUpdate = Partial<InvestigationCreate> & {
  status?: InvestigationStatus;
};
