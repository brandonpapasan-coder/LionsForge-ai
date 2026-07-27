export type RoadmapActionOutcomeStatus = "not_started" | "in_progress" | "review_ready" | "completed";
export type RoadmapActionOutcomeReason =
  | "adds_not_yet_demonstrated_competency"
  | "strengthens_developing_competency";

export type RoadmapActionOutcomeEntry = {
  learner_user_id: number;
  enrollment_id: number;
  outcome_status: RoadmapActionOutcomeStatus;
  template_slug: string;
  template_version: number;
  research_project_id: number;
  recommendation_reason_codes: RoadmapActionOutcomeReason[];
  action_sha256: string;
  action_receipt_sha256: string;
  acted_at: string;
  completed_at: string | null;
  completion_record_sha256: string | null;
};

export type RoadmapActionOutcomeBundle = {
  report: {
    schema: "lionsforge.roadmap-action-outcome-report";
    schema_version: 1;
    generator_version: string;
    learner_user_id: number;
    generated_at: string;
    entries: RoadmapActionOutcomeEntry[];
    excluded_record_count: number;
    excluded_findings: string[];
    advisory_notice: string;
  };
  receipt: {
    schema: "lionsforge.roadmap-action-outcome-report-receipt";
    schema_version: 1;
    generator_version: string;
    report_sha256: string;
    entry_count: number;
    completed_entry_count: number;
    excluded_record_count: number;
    generated_at: string;
  };
};

export type RoadmapActionOutcomeFilters = {
  templateSlug?: string;
  reasonCode?: RoadmapActionOutcomeReason | "";
  outcomeStatus?: RoadmapActionOutcomeStatus | "";
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
  if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "The outcome report could not be loaded.");
  return payload as T;
}

function utcBound(date: string, endOfDay = false): string {
  return new Date(`${date}T${endOfDay ? "23:59:59" : "00:00:00"}Z`).toISOString();
}

function queryString(filters: RoadmapActionOutcomeFilters): string {
  const params = new URLSearchParams();
  if (filters.templateSlug?.trim()) params.set("template_slug", filters.templateSlug.trim());
  if (filters.reasonCode) params.set("reason_code", filters.reasonCode);
  if (filters.outcomeStatus) params.set("outcome_status", filters.outcomeStatus);
  if (filters.actedAfter) params.set("acted_after", utcBound(filters.actedAfter));
  if (filters.actedBefore) params.set("acted_before", utcBound(filters.actedBefore, true));
  if (filters.completedAfter) params.set("completed_after", utcBound(filters.completedAfter));
  if (filters.completedBefore) params.set("completed_before", utcBound(filters.completedBefore, true));
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

export const roadmapActionOutcomeClient = {
  load: (filters: RoadmapActionOutcomeFilters = {}) => request<RoadmapActionOutcomeBundle>(`/roadmap-action-outcomes${queryString(filters)}`),
  validate: (bundle: RoadmapActionOutcomeBundle) =>
    request<{ valid: boolean; findings: string[] }>("/roadmap-action-outcomes/validate", {
      method: "POST",
      body: JSON.stringify(bundle),
    }),
};
