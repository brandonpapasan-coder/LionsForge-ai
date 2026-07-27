export type CompetencyGapStatus = "demonstrated" | "developing" | "not_yet_demonstrated";

export type CompetencyGapEntry = {
  competency_key: string;
  competency_label: string;
  supporting_completed_practicum_count: number;
  status: CompetencyGapStatus;
};

export type CompetencyGapRecommendation = {
  template_slug: string;
  template_version: number;
  objective_keys: string[];
  competency_keys: string[];
  estimated_minutes: number;
  prerequisite_lesson_slugs: string[];
  reason_codes: Array<
    "adds_not_yet_demonstrated_competency" | "strengthens_developing_competency"
  >;
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

async function requestGapPlan(): Promise<LearnerCompetencyGapPlanBundle> {
  const response = await fetch("/api/education/practica/competency-gap-plan", {
    cache: "no-store",
    headers: { "content-type": "application/json" },
  });
  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("Authentication required");
  }
  const payload = await response.json().catch(() => ({ detail: "Request failed" }));
  if (!response.ok) {
    throw new Error(typeof payload.detail === "string" ? payload.detail : "The competency roadmap could not be loaded.");
  }
  return payload as LearnerCompetencyGapPlanBundle;
}

export const competencyGapPlanClient = { load: requestGapPlan };
