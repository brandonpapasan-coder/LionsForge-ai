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

export type ResearchProjectOption = { id: number; title: string; status: string };
export type ResearchEvidenceOption = { id: number; project_id: number; title: string; source_type: string; tags: string[] };

async function practicumRequest<T>(path: string, init?: RequestInit): Promise<T> {
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
    const detail = typeof payload.detail === "string" ? payload.detail : payload.detail?.message;
    throw new Error(detail ?? "Request failed");
  }
  return payload as T;
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
};
