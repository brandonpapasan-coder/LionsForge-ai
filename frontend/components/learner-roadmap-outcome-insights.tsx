"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  roadmapOutcomeInsightClient,
  type RoadmapOutcomeInsightBundle,
  type RoadmapOutcomeInsightFilters,
  type RoadmapOutcomeInsightGroup,
  type RoadmapOutcomeReason,
  type RoadmapOutcomeStatus,
} from "@/lib/roadmap-outcome-insights";

const STATUS_LABELS: Record<RoadmapOutcomeStatus, string> = {
  not_started: "Not started",
  in_progress: "In progress",
  review_ready: "Review ready",
  completed: "Completed",
};

function percentage(value: number | null) {
  return value === null ? "Not available" : `${Math.round(value * 1000) / 10}%`;
}

function hours(value: number | null) {
  return value === null ? "Not available" : `${value.toLocaleString()} hours`;
}

function downloadBundle(bundle: RoadmapOutcomeInsightBundle) {
  const blob = new Blob([`${JSON.stringify(bundle, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `learner-roadmap-outcome-insights-${bundle.insights.learner_user_id}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function GroupRows({ title, rows, minimum }: { title: string; rows: RoadmapOutcomeInsightGroup[]; minimum: number }) {
  return <section aria-label={title}>
    <h3>{title}</h3>
    {rows.length === 0 ? <p>No groups match the current filters.</p> : rows.map((row) => <article key={row.group_key} aria-label={`${title}: ${row.group_key}`}>
      <h4>{row.group_key.replaceAll("_", " ")}</h4>
      <p>{row.action_count} actions · {row.completed_count} completed</p>
      {row.statistics_suppressed
        ? <p role="status">Rates and cycle-time statistics are hidden until this group has at least {minimum} actions.</p>
        : <p>Completed-action rate: {percentage(row.completed_rate)} · Median completion time: {hours(row.median_completion_hours)}</p>}
    </article>)}
  </section>;
}

export function LearnerRoadmapOutcomeInsights() {
  const [bundle, setBundle] = useState<RoadmapOutcomeInsightBundle | null>(null);
  const [filters, setFilters] = useState<RoadmapOutcomeInsightFilters>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [validation, setValidation] = useState<{ valid: boolean; findings: string[] } | null>(null);

  async function load(nextFilters: RoadmapOutcomeInsightFilters = filters) {
    setLoading(true); setError(null); setValidation(null);
    try { setBundle(await roadmapOutcomeInsightClient.load(nextFilters)); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Roadmap outcome insights could not be loaded."); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load({}); }, []);

  function applyFilters(event: FormEvent<HTMLFormElement>) { event.preventDefault(); void load(filters); }
  function clearFilters() { const cleared = {}; setFilters(cleared); void load(cleared); }
  async function validateBundle() {
    if (!bundle) return;
    try { setValidation(await roadmapOutcomeInsightClient.validate(bundle)); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "The insight bundle could not be validated."); }
  }

  return <section className="lesson-card" aria-labelledby="roadmap-outcome-insights-heading">
    <div className="lesson-meta"><span>workflow insights</span><span>{bundle?.insights.total_action_count ?? 0} actions</span></div>
    <h2 id="roadmap-outcome-insights-heading">Roadmap outcome insights</h2>
    <p>Summarize the current workflow progression of practica you explicitly started from roadmap recommendations.</p>
    <p>These insights are not proof of learning effectiveness, causation, accreditation, licensing, degree equivalence, professional certification, employment qualification or verification, individualized financial advice, autonomous competency approval, ranking, or prediction.</p>

    <form className="practicum-form-grid" aria-label="Filter roadmap outcome insights" onSubmit={applyFilters}>
      <label>Template slug<input value={filters.templateSlug ?? ""} onChange={(event) => setFilters({ ...filters, templateSlug: event.target.value })} /></label>
      <label>Recommendation reason<select value={filters.reasonCode ?? ""} onChange={(event) => setFilters({ ...filters, reasonCode: event.target.value as RoadmapOutcomeReason | "" })}><option value="">All reasons</option><option value="adds_not_yet_demonstrated_competency">Adds a competency not yet demonstrated</option><option value="strengthens_developing_competency">Strengthens a developing competency</option></select></label>
      <label>Outcome status<select value={filters.outcomeStatus ?? ""} onChange={(event) => setFilters({ ...filters, outcomeStatus: event.target.value as RoadmapOutcomeStatus | "" })}><option value="">All outcomes</option>{Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label>Acted on or after<input type="date" value={filters.actedAfter ?? ""} onChange={(event) => setFilters({ ...filters, actedAfter: event.target.value })} /></label>
      <label>Acted on or before<input type="date" value={filters.actedBefore ?? ""} onChange={(event) => setFilters({ ...filters, actedBefore: event.target.value })} /></label>
      <label>Completed on or after<input type="date" value={filters.completedAfter ?? ""} onChange={(event) => setFilters({ ...filters, completedAfter: event.target.value })} /></label>
      <label>Completed on or before<input type="date" value={filters.completedBefore ?? ""} onChange={(event) => setFilters({ ...filters, completedBefore: event.target.value })} /></label>
      <button type="submit" disabled={loading}>{loading ? "Applying filters…" : "Apply filters"}</button>
      <button type="button" onClick={clearFilters} disabled={loading}>Clear filters</button>
    </form>

    <p role="status" aria-live="polite">{loading ? "Loading roadmap outcome insights…" : bundle ? `${bundle.insights.total_action_count} actions are included in the current insight view.` : "Roadmap outcome insights unavailable."}</p>
    {error ? <p role="alert">{error}</p> : null}

    {bundle ? <>
      <div className="lesson-meta"><span>Insight digest</span><code>{bundle.receipt.insights_sha256}</code></div>
      <div className="lesson-meta"><span>Source report digest</span><code>{bundle.insights.source_report_sha256}</code></div>
      <div className="lesson-meta"><span>Generated</span><span>{new Date(bundle.insights.generated_at).toLocaleString()}</span></div>
      <p>Completed-action rate: <strong>{percentage(bundle.insights.completed_rate)}</strong></p>
      <p>Median completion time: <strong>{hours(bundle.insights.median_completion_hours)}</strong></p>
      <dl>{Object.entries(bundle.insights.status_counts).map(([status, count]) => <div key={status}><dt>{STATUS_LABELS[status as RoadmapOutcomeStatus]}</dt><dd>{count}</dd></div>)}</dl>
      <button type="button" onClick={() => downloadBundle(bundle)}>Export deterministic insight JSON</button>
      <button type="button" onClick={validateBundle}>Validate current insight bundle</button>
      {validation ? <p role="status" aria-live="polite">{validation.valid ? "Insight bundle validation passed." : `Insight bundle validation failed: ${validation.findings.join("; ")}`}</p> : null}
      {bundle.insights.source_excluded_record_count > 0 ? <p role="status">{bundle.insights.source_excluded_record_count} source record(s) were excluded because they failed integrity requirements.</p> : null}
      {bundle.insights.total_action_count === 0 ? <p>No roadmap outcome data matches the current filters.</p> : <>
        <GroupRows title="By practicum template" rows={bundle.insights.by_template} minimum={bundle.insights.minimum_group_size} />
        <GroupRows title="By recommendation reason" rows={bundle.insights.by_recommendation_reason} minimum={bundle.insights.minimum_group_size} />
      </>}
      <p>The export excludes project titles, research content, evidence summaries or titles, reflections, prompts, reviewer notes, credentials, private user content, answer keys, and hidden assessment metadata.</p>
    </> : null}
  </section>;
}
