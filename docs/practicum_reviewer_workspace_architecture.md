# Practicum Reviewer Workspace Architecture

## Purpose

The reviewer workspace gives explicitly authorized human reviewers a focused, auditable workflow for inspecting submitted research practica and recording append-only approval or revision-required decisions.

This feature extends the learner practicum foundation without introducing autonomous competency approval, accreditation, licensing, degree-equivalence, professional-certification claims, trading, brokerage, order routing, individualized financial advice, or security-selection recommendations.

## Authorization boundary

- Reviewer queue and decision endpoints require an authenticated user with explicit reviewer authorization.
- The initial implementation uses the existing `is_superuser` authorization boundary to remain consistent with the merged practicum review endpoint.
- Unauthorized callers receive a non-disclosing forbidden response and no queue metadata.
- Learner-facing enrollment endpoints remain owner-scoped and separate from reviewer-only endpoints.

## Reviewer queue

Proposed endpoint:

`GET /api/v1/education/practica/reviewer/queue`

Supported filters:

- `status`: `review_ready`, `revision_required`, or both
- `template_slug`
- `learner_query`: case-insensitive match against available learner identity fields
- `submitted_from`
- `submitted_to`
- `page`
- `page_size`

Default ordering is deterministic:

1. oldest submitted-for-review timestamp first
2. enrollment ID ascending as a stable tie-breaker

The response includes total count, page metadata, active filter values, and queue items.

## Queue item contract

Each item contains:

- enrollment ID and current status
- learner ID and display-safe identity fields
- template slug, version, and title
- linked project ID and title
- submitted-for-review timestamp and age
- latest human review decision, if any
- deterministic readiness summary
- objective-level counts for ready, missing, and approved states

The queue does not copy project evidence. Evidence remains referenced by its existing owner-scoped records.

## Reviewer detail

Proposed endpoint:

`GET /api/v1/education/practica/reviewer/enrollments/{enrollment_id}`

The detail response contains:

- queue-item context
- ordered objective definitions
- learner-authored reflections
- referenced evidence metadata and source categories
- deterministic readiness results and missing requirements
- append-only human review history
- a concurrency token based on the enrollment update timestamp and latest decision ID

The response clearly labels the provenance of each field:

- measured record
- learner-authored content
- deterministic system evaluation
- human reviewer decision

## Decision command

Proposed endpoint:

`POST /api/v1/education/practica/reviewer/enrollments/{enrollment_id}/decisions`

Payload:

- `decision`: `approved` or `revision_required`
- `notes`
- `expected_updated_at`
- `expected_latest_review_id`

Rules:

- Revision-required decisions require non-empty reviewer notes.
- Approval notes remain optional.
- Decisions are append-only.
- A stale concurrency token returns conflict rather than overwriting a newer decision.
- Approval moves the enrollment to `completed` and sets `completed_at`.
- Revision required moves the enrollment to `revision_required` and restores learner editing under the existing learner workflow.
- The endpoint re-evaluates readiness before accepting approval.
- Human approval is always explicit; deterministic readiness never completes an enrollment by itself.

## Frontend workspace

Proposed route:

`/education/reviewer/practica`

The workspace contains:

- queue summary counts
- status, template, learner, and date filters
- paginated submission list
- submission-age indicators that do not rely on color alone
- selected enrollment detail
- objective-level evidence and reflection review
- readiness gaps and provenance labels
- approval and revision-required decision forms
- required notes for revision decisions
- stale-decision recovery that reloads current review state

## Accessibility and responsive behavior

- All filters have explicit labels.
- Queue updates announce result counts through an `aria-live` region.
- Status is expressed with text and icons, not color alone.
- Decision controls have visible keyboard focus and touch-sized targets.
- Mobile layouts stack queue, detail, and decision panels in reading order.
- Reduced-motion preferences are respected.

## Test strategy

Backend coverage:

- reviewer authorization
- queue filtering and deterministic ordering
- pagination boundaries
- non-disclosing inaccessible enrollment behavior
- revision-notes requirement
- append-only decisions
- readiness recheck before approval
- stale decision conflict handling

Frontend coverage:

- authenticated proxy boundary
- queue filters and pagination controls
- provenance labels
- decision validation
- stale-decision recovery
- loading, empty, unauthorized, completed, and concurrent-decision states
- keyboard focus, touch target, reduced-motion, and responsive source contracts

## Delivery sequence

1. Add reviewer schemas and service helpers.
2. Add queue and detail endpoints.
3. Add concurrency-safe decision command.
4. Add backend tests.
5. Add typed frontend client and authenticated proxy.
6. Add reviewer route and workspace.
7. Add frontend tests and responsive styling.
8. Run all required CI gates before marking the PR ready.