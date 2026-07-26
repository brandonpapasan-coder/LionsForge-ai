"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  PracticumReviewerDetail,
  PracticumReviewerQueue,
  PracticumReviewerQueueFilters,
  researchPracticumReviewerClient,
} from "@/lib/research-practicum";

const initialFilters: PracticumReviewerQueueFilters = { page: 1, page_size: 20 };

export function PracticumReviewerWorkspace() {
  const [filters, setFilters] = useState(initialFilters);
  const [queue, setQueue] = useState<PracticumReviewerQueue | null>(null);
  const [detail, setDetail] = useState<PracticumReviewerDetail | null>(null);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const nextQueue = await researchPracticumReviewerClient.queue(filters);
      setQueue(nextQueue);
      if (detail && !nextQueue.items.some((item) => item.enrollment_id === detail.enrollment.enrollment_id)) {
        setDetail(null);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load reviewer queue");
    } finally {
      setLoading(false);
    }
  }, [detail, filters]);

  useEffect(() => {
    void loadQueue();
  }, [loadQueue]);

  async function openEnrollment(enrollmentId: number) {
    setError(null);
    try {
      setDetail(await researchPracticumReviewerClient.detail(enrollmentId));
      setNotes("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load practicum review");
    }
  }

  async function submitDecision(event: FormEvent, decision: "approved" | "revision_required") {
    event.preventDefault();
    if (!detail) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await researchPracticumReviewerClient.decide(
        detail.enrollment.enrollment_id,
        decision,
        notes,
        detail.enrollment.updated_at,
      );
      setDetail(updated);
      setNotes("");
      await loadQueue();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to record reviewer decision");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="reviewer-workspace">
      <header className="reviewer-header">
        <div>
          <p className="reviewer-eyebrow">Authorized human review</p>
          <h1>Research Practicum Review Queue</h1>
          <p>Inspect learner-authored reflections, linked research records, deterministic readiness, and append-only human decisions.</p>
        </div>
      </header>

      <section className="reviewer-filters" aria-label="Review queue filters">
        <label>
          Status
          <select
            value={filters.status ?? ""}
            onChange={(event) => setFilters({ ...filters, status: event.target.value || undefined, page: 1 })}
          >
            <option value="">All active reviews</option>
            <option value="review_ready">Ready for review</option>
            <option value="revision_required">Revision required</option>
          </select>
        </label>
        <label>
          Template slug
          <input
            value={filters.template_slug ?? ""}
            onChange={(event) => setFilters({ ...filters, template_slug: event.target.value || undefined, page: 1 })}
          />
        </label>
        <label>
          Learner ID
          <input
            type="number"
            min="1"
            value={filters.learner_user_id ?? ""}
            onChange={(event) => setFilters({ ...filters, learner_user_id: event.target.value ? Number(event.target.value) : undefined, page: 1 })}
          />
        </label>
        <button type="button" onClick={() => void loadQueue()} disabled={loading}>Refresh queue</button>
      </section>

      {error && <p className="reviewer-error" role="alert">{error}</p>}

      <div className="reviewer-layout">
        <section className="reviewer-queue" aria-busy={loading}>
          <div className="reviewer-section-heading">
            <h2>Submissions</h2>
            <span aria-live="polite">{queue?.total_items ?? 0} result(s)</span>
          </div>
          {loading ? (
            <p>Loading review queue…</p>
          ) : queue?.items.length ? (
            <ul>
              {queue.items.map((item) => (
                <li key={item.enrollment_id}>
                  <button type="button" onClick={() => void openEnrollment(item.enrollment_id)}>
                    <strong>{item.learner_display_name}</strong>
                    <span>{item.template_title}</span>
                    <span>{item.research_project_title}</span>
                    <small>{item.status.replaceAll("_", " ")}</small>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p>No practica match the current filters.</p>
          )}
          {queue && queue.total_pages > 1 && (
            <nav className="reviewer-pagination" aria-label="Review queue pages">
              <button
                type="button"
                disabled={queue.page <= 1}
                onClick={() => setFilters({ ...filters, page: queue.page - 1 })}
              >Previous</button>
              <span>Page {queue.page} of {queue.total_pages}</span>
              <button
                type="button"
                disabled={queue.page >= queue.total_pages}
                onClick={() => setFilters({ ...filters, page: queue.page + 1 })}
              >Next</button>
            </nav>
          )}
        </section>

        <section className="reviewer-detail" aria-label="Selected practicum review">
          {!detail ? (
            <p>Select a submission to inspect its evidence and readiness.</p>
          ) : (
            <>
              <div className="reviewer-section-heading">
                <div>
                  <p className="reviewer-eyebrow">{detail.enrollment.learner_display_name}</p>
                  <h2>{detail.enrollment.template_title}</h2>
                  <p>{detail.enrollment.research_project_title}</p>
                </div>
                <span>{detail.enrollment.status.replaceAll("_", " ")}</span>
              </div>

              <aside className="reviewer-advisory">{detail.advisory_notice}</aside>

              <div className="reviewer-objectives">
                {detail.objectives.map((objective) => (
                  <article key={objective.objective_key}>
                    <h3>{objective.sequence}. {objective.title}</h3>
                    <p>{objective.description}</p>
                    <p><strong>Competency:</strong> {objective.competency}</p>
                    <div>
                      <h4>Learner-authored reflection</h4>
                      <p>{objective.reflection || "No reflection provided."}</p>
                    </div>
                    <div>
                      <h4>Linked research records</h4>
                      {objective.evidence.length ? (
                        <ul>
                          {objective.evidence.map((evidence) => (
                            <li key={evidence.id}>
                              <strong>{evidence.title}</strong> — {evidence.source_type}
                              {evidence.summary && <p>{evidence.summary}</p>}
                            </li>
                          ))}
                        </ul>
                      ) : <p>No linked evidence.</p>}
                    </div>
                    <div>
                      <h4>Deterministic workflow evaluation</h4>
                      <p>{objective.readiness.status.replaceAll("_", " ")}</p>
                      {objective.readiness.missing_requirements.map((requirement) => <p key={requirement}>{requirement}</p>)}
                    </div>
                  </article>
                ))}
              </div>

              {detail.enrollment.status === "review_ready" && (
                <form className="reviewer-decision-form">
                  <label>
                    Reviewer notes
                    <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={5} maxLength={12000} />
                  </label>
                  <div>
                    <button type="button" disabled={saving} onClick={(event) => void submitDecision(event, "approved")}>Approve</button>
                    <button type="button" disabled={saving || !notes.trim()} onClick={(event) => void submitDecision(event, "revision_required")}>Request revision</button>
                  </div>
                  <p>Revision requests require reviewer notes. Decisions are recorded as append-only human review history.</p>
                </form>
              )}
            </>
          )}
        </section>
      </div>
    </main>
  );
}
