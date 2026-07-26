# Research Practicum and Competency Evidence Architecture

## Status

Implementation contract for GitHub issue #574. This document defines the first durable architecture for connecting LionsForge AI education records to owner-scoped research projects without copying, rewriting, or autonomously approving research evidence.

## Product intent

Research practica allow learners to demonstrate research competencies through traceable work performed inside LionsForge AI. Lesson completion and assessment scores remain useful preparation signals, but practicum completion requires linked project evidence, learner-authored reflection, deterministic readiness evaluation, and explicit human approval.

The system must distinguish four sources of information:

1. **Measured education records** — lesson progress, assessment attempts, competency mastery, and prerequisites.
2. **Research evidence references** — immutable references to evidence already stored within an owner-scoped research project.
3. **Learner-authored material** — reflections and explanations written by the learner.
4. **Human review decisions** — reviewer approval, revision requests, and review notes.

Deterministic system output may summarize readiness and missing requirements. It must not claim that a learner is professionally licensed, accredited, certified, or equivalent to a degree holder.

## Domain model

### PracticumTemplate

A versioned, system-defined template describing a practicum.

Required fields:

- `id`
- `slug`
- `version`
- `title`
- `description`
- `estimated_minutes`
- `prerequisite_lesson_slugs`
- `status` (`active` or `retired`)
- ordered competency objectives

Templates are immutable after learner enrollment. Material changes require a new version.

### PracticumObjective

An ordered objective belonging to one template version.

Required fields:

- `id`
- `template_id`
- `objective_key`
- `sequence`
- `title`
- `description`
- `competency`
- `required_evidence_categories`
- `minimum_evidence_count`
- `reflection_required`
- `human_review_required`

Objective ordering must be deterministic using `sequence`, then `objective_key`.

### PracticumEnrollment

An owner-scoped learner instance of a template linked to exactly one research project.

Required fields:

- `id`
- `user_id`
- `template_id`
- `template_version`
- `research_project_id`
- `status`
- `started_at`
- `submitted_for_review_at`
- `completed_at`
- `created_at`
- `updated_at`

Supported states:

- `not_started`
- `in_progress`
- `review_ready`
- `revision_required`
- `completed`

State transitions are explicit. `completed` requires a human approval record.

### PracticumObjectiveProgress

Learner-owned progress for one enrollment objective.

Required fields:

- `id`
- `enrollment_id`
- `objective_key`
- `reflection`
- `created_at`
- `updated_at`

Reflections are learner-authored and must be labeled as such in API responses and UI.

### PracticumEvidenceReference

A reference from an objective to an existing research evidence record.

Required fields:

- `id`
- `objective_progress_id`
- `research_evidence_id`
- `created_at`

The reference does not copy evidence content. Creation must verify that the evidence belongs to the enrollment's linked project and owner. Deleting a reference must not delete or mutate the evidence record.

### PracticumReviewDecision

An append-only human review record.

Required fields:

- `id`
- `enrollment_id`
- `reviewer_user_id`
- `decision` (`approved` or `revision_required`)
- `notes`
- `created_at`

The latest decision determines whether the enrollment may become `completed` or returns to `revision_required`. Prior decisions remain available for audit history.

## Readiness evaluation

The readiness service is deterministic and read-only. It evaluates each objective against the enrolled template version.

Each objective result includes:

- objective key and sequence
- competency
- status (`missing_requirements`, `ready_for_review`, `approved`)
- referenced evidence IDs
- evidence-category coverage
- reflection presence
- human-review requirement
- missing requirements

Enrollment readiness rules:

1. Missing prerequisites prevent enrollment creation.
2. An objective is `missing_requirements` when evidence-count, category, or reflection requirements are incomplete.
3. An objective is `ready_for_review` when deterministic requirements are satisfied but human approval is absent.
4. An objective is `approved` only when a human approval decision covers the submitted enrollment state.
5. An enrollment is `review_ready` only when every objective satisfies deterministic requirements.
6. An enrollment is `completed` only after explicit human approval.
7. A later revision-required decision moves the enrollment to `revision_required` without modifying evidence or deleting review history.

Readiness output must use stable ordering and include an advisory notice explaining that the result is a workflow evaluation, not accreditation or professional certification.

## Authorization and isolation

- Every enrollment query is scoped to the authenticated user unless a future reviewer role is explicitly authorized.
- Enrollment creation verifies ownership of the linked research project.
- Evidence attachment verifies that the evidence belongs to the linked project and authenticated owner.
- Inaccessible projects and evidence return not-found behavior rather than revealing resource existence.
- Reviewer operations require an explicit authorization policy; they must not be inferred from ordinary authentication.

## API surface

Initial authenticated routes under `/api/v1/education/practica`:

- `GET /templates`
- `GET /templates/{template_slug}`
- `POST /enrollments`
- `GET /enrollments`
- `GET /enrollments/{enrollment_id}`
- `PATCH /enrollments/{enrollment_id}/objectives/{objective_key}`
- `POST /enrollments/{enrollment_id}/objectives/{objective_key}/evidence`
- `DELETE /enrollments/{enrollment_id}/objectives/{objective_key}/evidence/{reference_id}`
- `POST /enrollments/{enrollment_id}/submit`
- `GET /enrollments/{enrollment_id}/readiness`
- `POST /enrollments/{enrollment_id}/reviews`

Write responses should return the refreshed enrollment or readiness representation so clients do not need to reconstruct state.

## Frontend workspace

The education workspace will add a Research Practicum section with:

- available template cards
- prerequisite status
- linked-project selection
- objective checklist
- project-evidence picker
- learner reflection editor
- deterministic readiness summary
- human-review history
- explicit source labels for measured records, research evidence, learner reflection, system evaluation, and reviewer decision

Loading, empty, unauthorized, inaccessible-project, validation-failure, revision-required, review-ready, and completed states must be represented in text and not through color alone.

## Delivery slices

### Slice 1 — persistence foundation

- Add models, relationships, indexes, constraints, and migration.
- Add template seed definitions.
- Add schema contracts.
- Add model and migration coverage.

### Slice 2 — enrollment and objective progress

- Add template listing and enrollment endpoints.
- Enforce prerequisites and owner-scoped project linking.
- Add reflection updates and evidence-reference management.
- Add authorization and immutability tests.

### Slice 3 — readiness and review

- Add deterministic readiness evaluation.
- Add submit and reviewer-decision workflows.
- Require human approval for completion.
- Add audit-history and transition tests.

### Slice 4 — frontend experience

- Add API proxy and typed client contracts.
- Build practicum workspace and state handling.
- Add component, interaction, and proxy tests.

### Slice 5 — release hardening

- Update API and user documentation.
- Run Backend CI, Frontend CI, Security Gate, and Deployment Validation.
- Verify no legacy finance module dependency is introduced.

## Non-goals

- Accreditation, degree equivalence, licensing, or professional certification.
- Autonomous competency approval.
- Copying project evidence into education records.
- Mutating evidence through practicum workflows.
- Live trading, brokerage integration, order routing, individualized financial advice, or security-selection recommendations.
