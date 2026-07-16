export type MarketLearningMasteryDimension = {
  key:
    | "scenario_breadth"
    | "risk_tier_comparison"
    | "evidence_discipline"
    | "review_follow_through"
    | "contradiction_handling"
    | "reflection_quality";
  title: string;
  status: "not_started" | "developing" | "met";
  evidence_count: number;
  target_count: number;
  criteria: string;
  unmet_criteria: string[];
  next_action: string;
};

export type MarketLearningMastery = {
  overall_readiness: "not_started" | "foundational" | "developing" | "evidence_informed";
  dimensions_met: number;
  dimensions_total: number;
  calculation_criteria: string[];
  dimensions: MarketLearningMasteryDimension[];
  disclaimer: string;
};
