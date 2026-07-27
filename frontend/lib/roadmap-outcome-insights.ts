export type RoadmapOutcomeStatus = "not_started" | "in_progress" | "review_ready" | "completed";
export type RoadmapOutcomeReason =
  | "adds_not_yet_demonstrated_competency"
  | "strengthens_developing_competency";

export type RoadmapOutcomeInsightGroup = {
  group_key: string;
  action_count: number;
  completed_count: number;
  completed_rate: number | null;
  median_completion_hours: number | null;
  statistics_suppressed: boolean;
};

export type RoadmapOutcomeInsightBundle = {
  insights: {
    schema: "lionsforge.roadmap-outcome-insights";
    schema_version: 1;
    generator_version: string;
    learner_user_id: number;
    generated_at: string;
    source_report_sha256: string;
    source_excluded_record_count: number;
    total_action_count: number;
    status_counts: Record<RoadmapOutcomeStatus, number>;
    completed_rate: number | null;
    median_completion_hours: number | null;
    by_template: RoadmapOutcomeInsightGroup[];
    by_recommendation_reason: RoadmapOutcomeInsightGroup[];
    minimum_group_size: number;
    advisory_notice: string;
  };
  receipt: {
    schema: "lionsforge.roadmap-outcome-insights-receipt";
    schema_version: 1;
    generator_version: string;
    insights_sha256: string;
    source_report_sha256: string;
    total_action_count: number;
    generated_at: string;
  };
};

export type RoadmapOutcomeInsightFilters = {
  templateSlug?: string;
  reasonCode?: RoadmapOutcomeReason | "";
  outcomeStatus?: RoadmapOutcomeStatus | "";
  actedAfter?: string;
  actedBefore?: string;
  completedAfter?: string;
  completedBefore?: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/education/practica${path}`, {
    ...init,
    cache: "no-store",
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
  });
  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("Authentication required");
  }
  const payload = await response.json().catch(() => ({ detail: "Request failed" }));
  if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Roadmap outcome insights could not be loaded.");
  return payload as T;
}

function queryString(filters: RoadmapOutcomeInsightFilters): string {
  const params = new URLSearchParams();
  if (filters.templateSlug?.trim()) params.set("template_slug", filters.templateSlug.trim());
  if (filters.reasonCode) params.set("reason_code", filters.reasonCode);
  if (filters.outcomeStatus) params.set("outcome_status", filters.outcomeStatus);
  if (filters.actedAfter) params.set("acted_after", new Date(`${filters.actedAfter}T00:00:00Z`).toISOString());
  if (filters.actedBefore) params.set("acted_before", new Date(`${filters.actedBefore}T23:59:59Z`).toISOString());
  if (filters.completedAfter) params.set("completed_after", new Date(`${filters.completedAfter}T00:00:00Z`).toISOString());
  if (filters.completedBefore) params.set("completed_before", new Date(`${filters.completedBefore}T23:59:59Z`).toISOString());
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

export const roadmapOutcomeInsightClient = {
  load: (filters: RoadmapOutcomeInsightFilters = {}) => request<RoadmapOutcomeInsightBundle>(`/roadmap-outcome-insights${queryString(filters)}`),
  validate: (bundle: RoadmapOutcomeInsightBundle) =>
    request<{ valid: boolean; findings: string[] }>("/roadmap-outcome-insights/validate", {
      method: "POST",
      body: JSON.stringify(bundle),
    }),
};
