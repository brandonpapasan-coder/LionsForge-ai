"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  roadmapActionOutcomeClient,
  type RoadmapActionOutcomeBundle,
  type RoadmapActionOutcomeFilters,
  type RoadmapActionOutcomeReason,
  type RoadmapActionOutcomeStatus,
} from "@/lib/roadmap-action-outcomes";

const REASON_LABELS: Record<RoadmapActionOutcomeReason, string> = {
  adds_not_yet_demonstrated_competency: "Added a competency not yet demonstrated",
  strengthens_developing_competency: "Strengthened a developing competency",
};

function downloadBundle(bundle: RoadmapActionOutcomeBundle) {
  const blob = new Blob([`${JSON.stringify(bundle, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `learner-roadmap-action-outcomes-${bundle.report.learner_user_id}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function LearnerRoadmapActionOutcomes() {
  const [bundle, setBundle] = useState<RoadmapActionOutcomeBundle | null>(null);
  const [filters, setFilters] = useState<RoadmapActionOutcomeFilters>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [validation, setValidation] = useState<{ valid: boolean; findings: string[] } | null>(null);

  async function load(nextFilters: RoadmapActionOutcomeFilters = filters) {
    setLoading(true);
    setError(null);
    setValidation(null);
    try {
      setBundle(await roadmapActionOutcomeClient.load(nextFilters));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "The outcome report could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load({}); }, []);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void load(filters);
  }

  function clearFilters() {
    const cleared: RoadmapActionOutcomeFilters = {};
    setFilters(cleared);
    void load(cleared);
  }

  async function validateBundle() {
    if (!bundle) return;
    setValidation(null);
    try {
      setValidation(await roadmapActionOutcomeClient.validate(bundle));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "The outcome bundle could not be validated.");
    }
  }

  return (
    <section className="lesson-card" aria-labelledby="roadmap-action-outcomes-heading">
      <div className="lesson-meta"><span>workflow progression</span><span>{bundle?.report.entries.length ?? 0} outcomes</span></div>
      <h2 id="roadmap-action-outcomes-heading">Roadmap action outcomes</h2>
      <p>Review the current workflow state of practica you explicitly started from competency-roadmap recommendations.</p>
      <p>This report is not accreditation, licensing, degree equivalence, professional certification, employment verification, individualized financial advice, autonomous competency approval, or proof that learning caused an external outcome.</p>

      <form className="practicum-form-grid" aria-label="Filter roadmap action outcomes" onSubmit={applyFilters}>
        <label>Template slug<input value={filters.templateSlug ?? ""} onChange={(event) => setFilters({ ...filters, templateSlug: event.target.value })} placeholder="source-validation-foundations" /></label>
        <label>Recommendation reason<select value={filters.reasonCode ?? ""} onChange={(event) => setFilters({ ...filters, reasonCode: event.target.value as RoadmapActionOutcomeReason | "" })}><option value="">All reasons</option><option value="adds_not_yet_demonstrated_competency">Adds a competency not yet demonstrated</option><option value="strengthens_developing_competency">Strengthens a developing competency</option></select></label>
        <label>Outcome status<select value={filters.outcomeStatus ?? ""} onChange={(event) => setFilters({ ...filters, outcomeStatus: event.target.value as RoadmapActionOutcomeStatus | "" })}><option value="">All outcomes</option><option value="not_started">Not started</option><option value="in_progress">In progress</option><option value="review_ready">Review ready</option><option value="completed">Completed</option></select></label>
        <label>Acted on or after<input type="date" value={filters.actedAfter ?? ""} onChange={(event) => setFilters({ ...filters, actedAfter: event.target.value })} /></label>
        <label>Acted on or before<input type="date" value={filters.actedBefore ?? ""} onChange={(event) => setFilters({ ...filters, actedBefore: event.target.value })} /></label>
        <label>Completed on or after<input type="date" value={filters.completedAfter ?? ""} onChange={(event) => setFilters({ ...filters, completedAfter: event.target.value })} /></label>
        <label>Completed on or before<input type="date" value={filters.completedBefore ?? ""} onChange={(event) => setFilters({ ...filters, completedBefore: event.target.value })} /></label>
        <button type="submit" disabled={loading}>{loading ? "Applying filters…" : "Apply filters"}</button>
        <button type="button" onClick={clearFilters} disabled={loading}>Clear filters</button>
      </form>

      <p role="status" aria-live="polite">{loading ? "Loading roadmap action outcomes…" : bundle ? `${bundle.report.entries.length} outcomes match the current filters.` : "Roadmap action outcomes unavailable."}</p>
      {error ? <p role="alert">{error}</p> : null}

      {bundle ? <>
        <div className="lesson-meta"><span>Report digest</span><code>{bundle.receipt.report_sha256}</code></div>
        <div className="lesson-meta"><span>Completed</span><span>{bundle.receipt.completed_entry_count} of {bundle.receipt.entry_count}</span></div>
        <div className="lesson-meta"><span>Generated</span><span>{new Date(bundle.report.generated_at).toLocaleString()}</span></div>
        <button type="button" onClick={() => downloadBundle(bundle)}>Export deterministic outcome JSON</button>
        <button type="button" onClick={validateBundle}>Validate current outcome bundle</button>
        {validation ? <p role="status" aria-live="polite">{validation.valid ? "Outcome bundle validation passed." : `Outcome bundle validation failed: ${validation.findings.join("; ")}`}</p> : null}
        <p>The export contains learner and enrollment identifiers, template and project identifiers, reason codes, workflow status, timestamps, and integrity digests. It excludes project titles, research content, evidence summaries, reflections, prompts, reviewer notes, credentials, private user content, answer keys, and hidden assessment metadata.</p>
        {bundle.report.excluded_record_count > 0 ? <p role="status">{bundle.report.excluded_record_count} stored record(s) were excluded because they failed integrity requirements.</p> : null}
        {bundle.report.entries.length === 0 ? <p>No roadmap action outcomes match the current filters.</p> : bundle.report.entries.map((entry) => <article key={entry.enrollment_id} aria-label={`Roadmap outcome for enrollment ${entry.enrollment_id}`}>
          <h3>{entry.template_slug} · version {entry.template_version}</h3>
          <p><strong>{entry.outcome_status.replaceAll("_", " ")}</strong> · acted {new Date(entry.acted_at).toLocaleString()}</p>
          {entry.completed_at ? <p>Completed {new Date(entry.completed_at).toLocaleString()}</p> : null}
          <p>Reason: {entry.recommendation_reason_codes.map((reason) => REASON_LABELS[reason]).join("; ")}</p>
          <p>Research project ID: <code>{entry.research_project_id}</code></p>
          <p>Action digest: <code>{entry.action_sha256}</code></p>
          {entry.completion_record_sha256 ? <p>Completion record digest: <code>{entry.completion_record_sha256}</code></p> : null}
          <a href={`/education?enrollment_id=${entry.enrollment_id}#research-practicum-workspace`}>Open enrollment {entry.enrollment_id}</a>
        </article>)}
      </> : null}
    </section>
  );
}
