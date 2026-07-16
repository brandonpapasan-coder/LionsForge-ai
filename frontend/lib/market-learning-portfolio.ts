export type MarketLearningPortfolioClaim = {
  session_id: number;
  evidence_id: number;
  scenario_name: string;
  risk_tier: string;
  claim: string;
  validation_status: string;
  reviewer_notes: string | null;
  review_event_count: number;
  next_reflection_prompt: string;
  completed_at: string;
};

export type MarketLearningPortfolio = {
  completed_sessions: number;
  unique_scenarios: number;
  scenario_counts: Record<string, number>;
  risk_tier_counts: Record<string, number>;
  submitted_evidence: number;
  validation_status_counts: Record<string, number>;
  immutable_review_events: number;
  learning_maturity: string;
  maturity_criteria: string[];
  recent_claims: MarketLearningPortfolioClaim[];
  disclaimer: string;
};
