export type MarketLearningRoadmapTask = {
  task_key: string;
  task_type: "resolve_evidence" | "submit_evidence" | "explore_scenario" | "compare_risk_tier";
  priority: number;
  title: string;
  rationale: string;
  completion_criteria: string;
  reflection_prompt: string;
  scenario_name: string | null;
  risk_tier: string | null;
  session_id: number | null;
  evidence_id: number | null;
};

export type MarketLearningRoadmap = {
  status: "not_started" | "active" | "complete";
  calculation_criteria: string[];
  tasks: MarketLearningRoadmapTask[];
  disclaimer: string;
};
