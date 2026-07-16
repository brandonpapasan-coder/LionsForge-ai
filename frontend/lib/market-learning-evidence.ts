export type MarketLearningSession = {
  id: number;
  account_id: number;
  scenario_name: string;
  steps: number;
  seed: number;
  risk_tier: string;
  projected_return: string;
  learner_reflection: string;
  status: string;
  completed_at: string;
};

export type ResearchProjectSummary = {
  id: number;
  title: string;
  description: string | null;
  objective: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type EvidenceRecord = {
  id: number;
  project_id: number | null;
  claim: string;
  validation_status: string;
  reviewer_notes: string | null;
  provenance: Record<string, unknown>;
};

export type EvidenceReviewEvent = {
  id: number;
  evidence_id: number;
  previous_status: string;
  validation_status: string;
  reviewer_notes: string | null;
  created_at: string;
};

export type MarketLearningEvidence = {
  link_id: number;
  session_id: number;
  project_id: number;
  evidence: EvidenceRecord;
  scenario_name: string;
  risk_tier: string;
  simulated_projected_return: string;
  learner_reflection: string;
  completed_at: string;
  classification: "simulated_educational_evidence";
  next_reflection_prompt: string;
  disclaimer: string;
};

export type MarketLearningEvidenceHistory = {
  evidence: MarketLearningEvidence;
  reviews: EvidenceReviewEvent[];
};
