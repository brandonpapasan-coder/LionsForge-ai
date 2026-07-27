export type RoadmapOutcomeTrendGranularity = "day" | "week" | "month";
export type RoadmapOutcomeTrendStatus = "not_started" | "in_progress" | "review_ready" | "completed";
export type RoadmapOutcomeTrendReason = "adds_not_yet_demonstrated_competency" | "strengthens_developing_competency";

export type RoadmapOutcomeTrendWindow = {
  window_start: string;
  window_end: string;
  action_count: number;
  status_counts: Record<RoadmapOutcomeTrendStatus, number>;
  completed_count: number;
  completed_rate: number | null;
  median_completion_hours: number | null;
  statistics_suppressed: boolean;
};

export type RoadmapOutcomeTrendBundle = {
  trends: {
    schema: "lionsforge.roadmap-outcome-trends";
    schema_version: 1;
    generator_version: string;
    learner_user_id: number;
    generated_at: string;
    source_report_sha256: string;
    source_excluded_record_count: number;
    granularity: RoadmapOutcomeTrendGranularity;
    range_start: string;
    range_end: string;
    minimum_window_size: number;
    windows: RoadmapOutcomeTrendWindow[];
    advisory_notice: string;
  };
  receipt: {
    schema: "lionsforge.roadmap-outcome-trends-receipt";
    schema_version: 1;
    generator_version: string;
    trends_sha256: string;
    source_report_sha256: string;
    window_count: number;
    generated_at: string;
  };
};

export type RoadmapOutcomeTrendFilters = {
  granularity: RoadmapOutcomeTrendGranularity;
  rangeStart: string;
  rangeEnd: string;
  templateSlug?: string;
  reasonCode?: RoadmapOutcomeTrendReason | "";
  outcomeStatus?: RoadmapOutcomeTrendStatus | "";
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
  if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Roadmap outcome trends could not be loaded.");
  return payload as T;
}

function queryString(filters: RoadmapOutcomeTrendFilters): string {
  const params = new URLSearchParams({
    granularity: filters.granularity,
    range_start: new Date(`${filters.rangeStart}T00:00:00Z`).toISOString(),
    range_end: new Date(`${filters.rangeEnd}T23:59:59Z`).toISOString(),
  });
  if (filters.templateSlug?.trim()) params.set("template_slug", filters.templateSlug.trim());
  if (filters.reasonCode) params.set("reason_code", filters.reasonCode);
  if (filters.outcomeStatus) params.set("outcome_status", filters.outcomeStatus);
  return `?${params.toString()}`;
}

export const roadmapOutcomeTrendClient = {
  load: (filters: RoadmapOutcomeTrendFilters) => request<RoadmapOutcomeTrendBundle>(`/roadmap-outcome-trends${queryString(filters)}`),
  validate: (bundle: RoadmapOutcomeTrendBundle) => request<{ valid: boolean; findings: string[] }>("/roadmap-outcome-trends/validate", {
    method: "POST",
    body: JSON.stringify(bundle),
  }),
};
