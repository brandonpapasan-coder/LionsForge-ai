export type KnowledgeQualityRisk = {
  risk_type: string;
  severity: number;
  title: string;
  detail: string;
  source_ids: number[];
};

export type KnowledgeQualityActivity = {
  record_type: string;
  record_id: number;
  title: string;
  status: string;
  occurred_at: string;
};

export type KnowledgeQualityDashboard = {
  project_id: number | null;
  methodology_version: string;
  generated_at: string;
  health_score: number;
  health_components: Record<string, number>;
  memories: {
    total: number;
    validated: number;
    provisional: number;
    contested: number;
    superseded: number;
    archived: number;
    stale: number;
  };
  evidence_total: number;
  evidence_approved: number;
  evidence_pending_review: number;
  evidence_coverage_ratio: number;
  average_confidence: number;
  median_confidence: number;
  contradiction_rate: number;
  unresolved_contradictions: number;
  federation_links: number;
  federation_coverage_ratio: number;
  missions: Record<string, number>;
  planning: Record<string, number>;
  knowledge_revision_velocity: number;
  review_backlog: number;
  top_risks: KnowledgeQualityRisk[];
  top_priorities: Array<Record<string, unknown>>;
  recent_activity: KnowledgeQualityActivity[];
};
