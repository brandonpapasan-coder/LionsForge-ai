export type RoadmapActionReason =
  | "adds_not_yet_demonstrated_competency"
  | "strengthens_developing_competency";

export type RoadmapActionLedgerEntry = {
  learner_user_id: number;
  enrollment_id: number;
  enrollment_status: "not_started" | "in_progress" | "review_ready" | "completed";
  template_slug: string;
  template_version: number;
  research_project_id: number;
  recommendation_reason_codes: RoadmapActionReason[];
  roadmap_plan_sha256: string;
  portfolio_sha256: string;
  action_sha256: string;
  action_receipt_sha256: string;
  acted_at: string;
};

export type RoadmapActionLedgerBundle = {
  ledger: {
    schema: "lionsforge.roadmap-action-ledger";
    schema_version: 1;
    generator_version: string;
    learner_user_id: number;
    generated_at: string;
    entries: RoadmapActionLedgerEntry[];
    excluded_record_count: number;
    excluded_findings: string[];
    advisory_notice: string;
  };
  receipt: {
    schema: "lionsforge.roadmap-action-ledger-receipt";
    schema_version: 1;
    generator_version: string;
    ledger_sha256: string;
    entry_count: number;
    excluded_record_count: number;
    generated_at: string;
  };
};

export type RoadmapActionLedgerFilters = {
  templateSlug?: string;
  reasonCode?: RoadmapActionReason | "";
  actedAfter?: string;
  actedBefore?: string;
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
  if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "The action history could not be loaded.");
  return payload as T;
}

function queryString(filters: RoadmapActionLedgerFilters): string {
  const params = new URLSearchParams();
  if (filters.templateSlug?.trim()) params.set("template_slug", filters.templateSlug.trim());
  if (filters.reasonCode) params.set("reason_code", filters.reasonCode);
  if (filters.actedAfter) params.set("acted_after", new Date(`${filters.actedAfter}T00:00:00Z`).toISOString());
  if (filters.actedBefore) params.set("acted_before", new Date(`${filters.actedBefore}T23:59:59Z`).toISOString());
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

export const roadmapActionLedgerClient = {
  load: (filters: RoadmapActionLedgerFilters = {}) => request<RoadmapActionLedgerBundle>(`/roadmap-action-ledger${queryString(filters)}`),
  validate: (bundle: RoadmapActionLedgerBundle) =>
    request<{ valid: boolean; findings: string[] }>("/roadmap-action-ledger/validate", {
      method: "POST",
      body: JSON.stringify(bundle),
    }),
};
