export type ResearchTrustIndexComponent = {
  key: string;
  label: string;
  score: number;
  weight: number;
  weighted_score: number;
  explanation: string;
  recommendations: string[];
};

export type ResearchTrustIndex = {
  project_id: number;
  overall_score: number;
  confidence_level: string;
  evidence_count: number;
  supporting_count: number;
  contradicting_count: number;
  approved_count: number;
  conflict_count: number;
  review_event_count: number;
  reviewed_evidence_count: number;
  review_reversal_count: number;
  components: ResearchTrustIndexComponent[];
  strengths: string[];
  limitations: string[];
  recommended_actions: string[];
  methodology_version: string;
};
