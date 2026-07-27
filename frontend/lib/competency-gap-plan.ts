export type CompetencyGapStatus = "demonstrated" | "developing" | "not_yet_demonstrated";

export type CompetencyGapEntry = {
  competency_key: string;
  competency_label: string;
  supporting_completed_practicum_count: number;
  status: CompetencyGapStatus;
};

export type CompetencyGapRecommendationReason =
  | "adds_not_yet_demonstrated_competency"
  | "strengthens_developing_competency";

export type CompetencyGapRecommendation = {
  template_slug: string;
  template_version: number;
  objective_keys: string[];
  competency_keys: string[];
  estimated_minutes: number;
  prerequisite_lesson_slugs: string[];
  reason_codes: CompetencyGapRecommendationReason[];
};

export type LearnerCompetencyGapPlan = {
  schema: "lionsforge.learner-competency-gap-plan";
  schema_version: 1;
  generator_version: string;
  learner_user_id: number;
  generated_at: string;
  portfolio_sha256: string;
  thresholds: { demonstrated_minimum_completed_practica: number };
  competencies: CompetencyGapEntry[];
  recommendations: CompetencyGapRecommendation[];
  advisory_notice: string;
};

export type LearnerCompetencyGapPlanReceipt = {
  schema: "lionsforge.learner-competency-gap-plan-receipt";
  schema_version: 1;
  generator_version: string;
  plan_sha256: string;
  portfolio_sha256: string;
  generated_at: string;
};

export type LearnerCompetencyGapPlanBundle = {
  plan: LearnerCompetencyGapPlan;
  receipt: LearnerCompetencyGapPlanReceipt;
  source_portfolio_excluded_record_count: number;
};

export type RoadmapEnrollmentAction = {
  schema: "lionsforge.roadmap-practicum-enrollment-action";
  schema_version: 1;
  generator_version: string;
  action_source: "explicit_learner_request";
  learner_user_id: number;
  enrollment_id: number;
  enrollment_status: "not_started" | "in_progress";
  template_slug: string;
  template_version: number;
  research_project_id: number;
  recommendation_reason_codes: CompetencyGapRecommendationReason[];
  roadmap_plan_sha256: string;
  portfolio_sha256: string;
  acted_at: string;
  advisory_notice: string;
};

export type RoadmapEnrollmentReceipt = {
  schema: "lionsforge.roadmap-practicum-enrollment-action-receipt";
  schema_version: 1;
  generator_version: string;
  action_sha256: string;
  roadmap_plan_sha256: string;
  portfolio_sha256: string;
  generated_at: string;
};

export type RoadmapEnrollmentBundle = {
  action: RoadmapEnrollmentAction;
  receipt: RoadmapEnrollmentReceipt;
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
  if (!response.ok) {
    const detail = payload.detail;
    if (typeof detail === "string") throw new Error(detail);
    if (detail?.message === "Practicum prerequisites are incomplete") {
      const missing = Array.isArray(detail.missing_lesson_slugs) ? detail.missing_lesson_slugs.join(", ") : "required lessons";
      throw new Error(`Complete these prerequisite lessons first: ${missing}`);
    }
    throw new Error(detail?.message ?? "The roadmap action could not be completed.");
  }
  return payload as T;
}

export const competencyGapPlanClient = {
  load: () => request<LearnerCompetencyGapPlanBundle>("/competency-gap-plan"),
  startRecommendedPracticum: (template_slug: string, template_version: number, research_project_id: number) =>
    request<RoadmapEnrollmentBundle>("/roadmap-practicum-enrollment", {
      method: "POST",
      body: JSON.stringify({ template_slug, template_version, research_project_id }),
    }),
};
