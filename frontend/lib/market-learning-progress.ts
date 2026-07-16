export type MarketLearningProgress = {
  total_sessions: number;
  completed_sessions: number;
  unique_scenarios: number;
  scenario_counts: Record<string, number>;
  risk_tier_counts: Record<string, number>;
  average_projected_return: string;
  latest_completed_at: string | null;
  proficiency_level: "not_started" | "foundational" | "developing" | "proficient";
  evidence_badge_eligible: boolean;
  next_learning_step: string;
  disclaimer: string;
};
