export type PracticumEnrollmentStatus =
  | "not_started"
  | "in_progress"
  | "review_ready"
  | "revision_required"
  | "completed";

export type PracticumObjective = {
  objective_key: string;
  sequence: number;
  title: string;
  description: string;
  competency: string;
  required_evidence_categories: string[];
  minimum_evidence_count: number;
  reflection_required: boolean;
  human_review_required: boolean;
};

export type PracticumTemplate = {
  id: number;
  slug: string;
  version: number;
  title: string;
  description: string;
  estimated_minutes: number;
  prerequisite_lesson_slugs: string[];
  status: "active" | "retired";
  objectives: PracticumObjective[];
};

export type PracticumEvidenceReference = {
  id: number;
  research_evidence_id: number;
  created_at: string;
};

export type PracticumObjectiveProgress = {
  objective_key: string;
  reflection: string | null;
  reflection_source: "learner_authored";
  evidence_references: PracticumEvidenceReference[];
  created_at: string;
  updated_at: string;
};

export type PracticumReviewDecision = {
  id: number;
  reviewer_user_id: number;
  decision: "approved" | "revision_required";
  notes: string | null;
  decision_source: "human_reviewer";
  created_at: string;
};

export type PracticumEnrollment = {
  id: number;
  user_id: number;
  template_slug: string;
  template_version: number;
  research_project_id: number;
  status: PracticumEnrollmentStatus;
  started_at: string | null;
  submitted_for_review_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  objectives: PracticumObjectiveProgress[];
  review_history: PracticumReviewDecision[];
};

export type PracticumObjectiveReadiness = {
  objective_key: string;
  sequence: number;
  competency: string;
  status: "missing_requirements" | "ready_for_review" | "approved";
  referenced_evidence_ids: number[];
  covered_evidence_categories: string[];
  reflection_present: boolean;
  human_review_required: boolean;
  missing_requirements: string[];
};

export type PracticumReadiness = {
  enrollment_id: number;
  enrollment_status: PracticumEnrollmentStatus;
  system_evaluation_source: "deterministic_rules";
  advisory_notice: string;
  objectives: PracticumObjectiveReadiness[];
  missing_requirements: string[];
  ready_for_human_review: boolean;
  latest_review_decision: PracticumReviewDecision | null;
};

export type PracticumCompletionAuditObjective = {
  objective_key: string;
  sequence: number;
  status: "approved";
  referenced_evidence_ids: number[];
};

export type PracticumCompletionAuditDecision = {
  decision_id: number;
  reviewer_user_id: number;
  decision: "approved" | "revision_required";
  created_at: string;
  decision_source: "human_reviewer";
};

export type PracticumCompletionAuditRecord = {
  schema: "lionsforge.practicum-completion-record";
  schema_version: 1;
  generator_version: string;
  enrollment_id: number;
  learner_user_id: number;
  template_slug: string;
  template_version: number;
  research_project_id: number;
  status: "completed";
  completed_at: string;
  objectives: PracticumCompletionAuditObjective[];
  review_history: PracticumCompletionAuditDecision[];
  advisory_notice: string;
};

export type PracticumCompletionAuditReceipt = {
  schema: "lionsforge.practicum-completion-receipt";
  schema_version: 1;
  generator_version: string;
  record_sha256: string;
  generated_at: string;
};

export type PracticumCompletionAuditBundle = {
  record: PracticumCompletionAuditRecord;
  receipt: PracticumCompletionAuditReceipt;
};

export type PracticumReviewerEvidence = {
  id: number;
  title: string;
  summary: string | null;
  source_type: string;
  status: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  record_source: "measured_research_record";
};

export type PracticumReviewerObjective = {
  objective_key: string;
  sequence: number;
  title: string;
  description: string;
  competency: string;
  reflection: string | null;
  reflection_source: "learner_authored";
  evidence: PracticumReviewerEvidence[];
  readiness: PracticumObjectiveReadiness;
};

export type PracticumReviewerQueueItem = {
  enrollment_id: number;
  learner_user_id: number;
  learner_display_name: string;
  template_slug: string;
  template_title: string;
  template_version: number;
  research_project_id: number;
  research_project_title: string;
  status: PracticumEnrollmentStatus;
  submitted_for_review_at: string | null;
  updated_at: string;
  latest_review_decision: PracticumReviewDecision | null;
};

export type PracticumReviewerQueue = {
  items: PracticumReviewerQueueItem[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
};

export type PracticumReviewerDetail = {
  enrollment: PracticumReviewerQueueItem;
  objectives: PracticumReviewerObjective[];
  readiness: PracticumReadiness;
  review_history: PracticumReviewDecision[];
  human_review_required: true;
  advisory_notice: string;
};

export type PracticumReviewerQueueFilters = {
  status?: "review_ready" | "revision_required";
  template_slug?: string;
  learner_user_id?: number;
  learner_query?: string;
  submitted_from?: string;
  submitted_to?: string;
  page?: number;
  page_size?: number;
};

export type ResearchProjectOption = { id: number; title: string; status: string };
export type ResearchEvidenceOption = { id: number; project_id: number; title: string; source_type: string; tags: string[] };

export class PracticumRequestError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "PracticumRequestError";
  }
}

async function practicumRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/education/practica${path}`, {
    ...init,
    cache: "no-store",
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
  });
  if (response.status === 401) {
    window.location.href = "/login";
    throw new PracticumRequestError("Authentication required", response.status);
  }
  const payload = await response.json().catch(() => ({ detail: "Request failed" }));
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : payload.detail?.message;
    throw new PracticumRequestError(detail ?? "Request failed", response.status);
  }
  return payload as T;
}

function reviewerQueueQuery(filters: PracticumReviewerQueueFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.template_slug) params.set("template_slug", filters.template_slug);
  if (filters.learner_user_id) params.set("learner_user_id", String(filters.learner_user_id));
  if (filters.learner_query?.trim()) params.set("learner_query", filters.learner_query.trim());
  if (filters.submitted_from) params.set("submitted_from", filters.submitted_from);
  if (filters.submitted_to) params.set("submitted_to", filters.submitted_to);
  params.set("page", String(filters.page ?? 1));
  params.set("page_size", String(filters.page_size ?? 25));
  return params.toString();
}

export const researchPracticumClient = {
  templates: () => practicumRequest<PracticumTemplate[]>("/templates"),
  enrollments: () => practicumRequest<PracticumEnrollment[]>("/enrollments"),
  createEnrollment: (template_slug: string, research_project_id: number) =>
    practicumRequest<PracticumEnrollment>("/enrollments", {
      method: "POST",
      body: JSON.stringify({ template_slug, research_project_id }),
    }),
  updateReflection: (enrollmentId: number, objectiveKey: string, reflection: string) =>
    practicumRequest<PracticumEnrollment>(`/enrollments/${enrollmentId}/objectives/${objectiveKey}`, {
      method: "PATCH",
      body: JSON.stringify({ reflection }),
    }),
  attachEvidence: (enrollmentId: number, objectiveKey: string, research_evidence_id: number) =>
    practicumRequest<PracticumEnrollment>(`/enrollments/${enrollmentId}/objectives/${objectiveKey}/evidence`, {
      method: "POST",
      body: JSON.stringify({ research_evidence_id }),
    }),
  removeEvidence: (enrollmentId: number, objectiveKey: string, referenceId: number) =>
    practicumRequest<PracticumEnrollment>(`/enrollments/${enrollmentId}/objectives/${objectiveKey}/evidence/${referenceId}`, {
      method: "DELETE",
    }),
  readiness: (enrollmentId: number) =>
    practicumRequest<PracticumReadiness>(`/enrollments/${enrollmentId}/readiness`),
  submit: (enrollmentId: number) =>
    practicumRequest<PracticumReadiness>(`/enrollments/${enrollmentId}/submit`, { method: "POST" }),
  completionAudit: (enrollmentId: number) =>
    practicumRequest<PracticumCompletionAuditBundle>(`/enrollments/${enrollmentId}/completion-audit`, {
      method: "POST",
    }),
  reviewerQueue: (filters: PracticumReviewerQueueFilters = {}) =>
    practicumRequest<PracticumReviewerQueue>(`/reviewer/queue?${reviewerQueueQuery(filters)}`),
  reviewerDetail: (enrollmentId: number) =>
    practicumRequest<PracticumReviewerDetail>(`/reviewer/enrollments/${enrollmentId}`),
  reviewerDecision: (
    enrollmentId: number,
    decision: "approved" | "revision_required",
    notes: string,
    expected_enrollment_updated_at: string,
  ) =>
    practicumRequest<PracticumReviewerDetail>(`/reviewer/enrollments/${enrollmentId}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision, notes, expected_enrollment_updated_at }),
    }),
};

export const researchPracticumReviewerClient = {
  queue: researchPracticumClient.reviewerQueue,
  detail: researchPracticumClient.reviewerDetail,
  decide: researchPracticumClient.reviewerDecision,
};
