"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  roadmapActionLedgerClient,
  type RoadmapActionLedgerBundle,
  type RoadmapActionLedgerFilters,
  type RoadmapActionReason,
} from "@/lib/roadmap-action-ledger";

const REASON_LABELS: Record<RoadmapActionReason, string> = {
  adds_not_yet_demonstrated_competency: "Added a competency not yet demonstrated",
  strengthens_developing_competency: "Strengthened a developing competency",
};

function downloadBundle(bundle: RoadmapActionLedgerBundle) {
  const blob = new Blob([`${JSON.stringify(bundle, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `learner-roadmap-action-ledger-${bundle.ledger.learner_user_id}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function LearnerRoadmapActionHistory() {
  const [bundle, setBundle] = useState<RoadmapActionLedgerBundle | null>(null);
  const [filters, setFilters] = useState<RoadmapActionLedgerFilters>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [validation, setValidation] = useState<{ valid: boolean; findings: string[] } | null>(null);

  async function load(nextFilters: RoadmapActionLedgerFilters = filters) {
    setLoading(true);
    setError(null);
    setValidation(null);
    try {
      setBundle(await roadmapActionLedgerClient.load(nextFilters));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "The action history could not be loaded.");
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
    const cleared: RoadmapActionLedgerFilters = {};
    setFilters(cleared);
    void load(cleared);
  }

  async function validateBundle() {
    if (!bundle) return;
    setValidation(null);
    try {
      setValidation(await roadmapActionLedgerClient.validate(bundle));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "The ledger bundle could not be validated.");
    }
  }

  return (
    <section className="lesson-card" aria-labelledby="roadmap-action-history-heading">
      <div className="lesson-meta"><span>privacy-safe provenance</span><span>{bundle?.ledger.entries.length ?? 0} recorded actions</span></div>
      <h2 id="roadmap-action-history-heading">Roadmap action history</h2>
      <p>Review the deterministic history of practica you explicitly started from competency-roadmap recommendations.</p>
      <p>This integrity history is not accreditation, licensing, degree equivalence, professional certification, employment verification, individualized financial advice, or autonomous competency approval.</p>

      <form className="practicum-form-grid" aria-label="Filter roadmap action history" onSubmit={applyFilters}>
        <label>Template slug<input value={filters.templateSlug ?? ""} onChange={(event) => setFilters({ ...filters, templateSlug: event.target.value })} placeholder="source-validation-foundations" /></label>
        <label>Recommendation reason<select value={filters.reasonCode ?? ""} onChange={(event) => setFilters({ ...filters, reasonCode: event.target.value as RoadmapActionReason | "" })}><option value="">All reasons</option><option value="adds_not_yet_demonstrated_competency">Adds a competency not yet demonstrated</option><option value="strengthens_developing_competency">Strengthens a developing competency</option></select></label>
        <label>Acted on or after<input type="date" value={filters.actedAfter ?? ""} onChange={(event) => setFilters({ ...filters, actedAfter: event.target.value })} /></label>
        <label>Acted on or before<input type="date" value={filters.actedBefore ?? ""} onChange={(event) => setFilters({ ...filters, actedBefore: event.target.value })} /></label>
        <button type="submit" disabled={loading}>{loading ? "Applying filters…" : "Apply filters"}</button>
        <button type="button" onClick={clearFilters} disabled={loading}>Clear filters</button>
      </form>

      <p role="status" aria-live="polite">{loading ? "Loading roadmap action history…" : bundle ? `${bundle.ledger.entries.length} actions match the current filters.` : "Roadmap action history unavailable."}</p>
      {error ? <p role="alert">{error}</p> : null}

      {bundle ? <>
        <div className="lesson-meta"><span>Ledger digest</span><code>{bundle.receipt.ledger_sha256}</code></div>
        <div className="lesson-meta"><span>Generated</span><span>{new Date(bundle.ledger.generated_at).toLocaleString()}</span></div>
        <button type="button" onClick={() => downloadBundle(bundle)}>Export deterministic ledger JSON</button>
        <button type="button" onClick={validateBundle}>Validate current ledger bundle</button>
        {validation ? <p role="status" aria-live="polite">{validation.valid ? "Ledger bundle validation passed." : `Ledger bundle validation failed: ${validation.findings.join("; ")}`}</p> : null}
        <p>The export contains learner and enrollment identifiers, template and project identifiers, reason codes, status, timestamps, schema versions, and integrity digests. It excludes project titles, research content, evidence summaries, reflections, prompts, reviewer notes, credentials, private user content, answer keys, and hidden assessment metadata.</p>
        {bundle.ledger.excluded_record_count > 0 ? <p role="status">{bundle.ledger.excluded_record_count} stored record(s) were excluded because they failed integrity requirements.</p> : null}
        {bundle.ledger.entries.length === 0 ? <p>No roadmap actions match the current filters.</p> : bundle.ledger.entries.map((entry) => <article key={entry.enrollment_id} aria-label={`Roadmap action for enrollment ${entry.enrollment_id}`}>
          <h3>{entry.template_slug} · version {entry.template_version}</h3>
          <p><strong>{entry.enrollment_status.replaceAll("_", " ")}</strong> · acted {new Date(entry.acted_at).toLocaleString()}</p>
          <p>Reason: {entry.recommendation_reason_codes.map((reason) => REASON_LABELS[reason]).join("; ")}</p>
          <p>Research project ID: <code>{entry.research_project_id}</code></p>
          <p>Action digest: <code>{entry.action_sha256}</code></p>
          <a href={`/education?enrollment_id=${entry.enrollment_id}#research-practicum-workspace`}>Open enrollment {entry.enrollment_id}</a>
        </article>)}
      </> : null}
    </section>
  );
}
