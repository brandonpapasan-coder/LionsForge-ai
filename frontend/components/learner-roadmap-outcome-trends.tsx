"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  roadmapOutcomeTrendClient,
  type RoadmapOutcomeTrendBundle,
  type RoadmapOutcomeTrendFilters,
  type RoadmapOutcomeTrendGranularity,
  type RoadmapOutcomeTrendReason,
  type RoadmapOutcomeTrendStatus,
} from "@/lib/roadmap-outcome-trends";

const STATUS_LABELS: Record<RoadmapOutcomeTrendStatus, string> = {
  not_started: "Not started",
  in_progress: "In progress",
  review_ready: "Review ready",
  completed: "Completed",
};

function dateOffset(days: number) {
  const value = new Date();
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}

const DEFAULT_FILTERS: RoadmapOutcomeTrendFilters = {
  granularity: "week",
  rangeStart: dateOffset(-84),
  rangeEnd: dateOffset(0),
};

function percentage(value: number | null) {
  return value === null ? "Suppressed" : `${Math.round(value * 1000) / 10}%`;
}

function hours(value: number | null) {
  return value === null ? "Suppressed" : `${value.toLocaleString()} hours`;
}

function downloadBundle(bundle: RoadmapOutcomeTrendBundle) {
  const blob = new Blob([`${JSON.stringify(bundle, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `learner-roadmap-outcome-trends-${bundle.trends.learner_user_id}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function LearnerRoadmapOutcomeTrends() {
  const [bundle, setBundle] = useState<RoadmapOutcomeTrendBundle | null>(null);
  const [filters, setFilters] = useState<RoadmapOutcomeTrendFilters>(DEFAULT_FILTERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [validation, setValidation] = useState<{ valid: boolean; findings: string[] } | null>(null);

  async function load(nextFilters: RoadmapOutcomeTrendFilters = filters) {
    setLoading(true); setError(null); setValidation(null);
    try { setBundle(await roadmapOutcomeTrendClient.load(nextFilters)); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Roadmap outcome trends could not be loaded."); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(DEFAULT_FILTERS); }, []);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (filters.rangeEnd <= filters.rangeStart) {
      setError("The end date must be after the start date.");
      return;
    }
    void load(filters);
  }

  async function validateBundle() {
    if (!bundle) return;
    try { setValidation(await roadmapOutcomeTrendClient.validate(bundle)); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "The trend bundle could not be validated."); }
  }

  return <section className="lesson-card" aria-labelledby="roadmap-outcome-trends-heading">
    <div className="lesson-meta"><span>workflow trend snapshots</span><span>{bundle?.trends.windows.length ?? 0} UTC windows</span></div>
    <h2 id="roadmap-outcome-trends-heading">Roadmap outcome trend snapshots</h2>
    <p>Compare bounded workflow-progression summaries over daily, weekly, or monthly UTC windows.</p>
    <p>These snapshots do not prove learning effectiveness or causation and do not provide ranking, forecasting, prediction, accreditation, licensing, certification, employment qualification, or individualized financial advice.</p>

    <form className="practicum-form-grid" aria-label="Filter roadmap outcome trend snapshots" onSubmit={applyFilters}>
      <label>Window size<select value={filters.granularity} onChange={(event) => setFilters({ ...filters, granularity: event.target.value as RoadmapOutcomeTrendGranularity })}><option value="day">Daily</option><option value="week">Weekly</option><option value="month">Monthly</option></select></label>
      <label>Start date (UTC)<input required type="date" value={filters.rangeStart} onChange={(event) => setFilters({ ...filters, rangeStart: event.target.value })} /></label>
      <label>End date (UTC)<input required type="date" value={filters.rangeEnd} onChange={(event) => setFilters({ ...filters, rangeEnd: event.target.value })} /></label>
      <label>Template slug<input value={filters.templateSlug ?? ""} onChange={(event) => setFilters({ ...filters, templateSlug: event.target.value })} /></label>
      <label>Recommendation reason<select value={filters.reasonCode ?? ""} onChange={(event) => setFilters({ ...filters, reasonCode: event.target.value as RoadmapOutcomeTrendReason | "" })}><option value="">All reasons</option><option value="adds_not_yet_demonstrated_competency">Adds a competency not yet demonstrated</option><option value="strengthens_developing_competency">Strengthens a developing competency</option></select></label>
      <label>Outcome status<select value={filters.outcomeStatus ?? ""} onChange={(event) => setFilters({ ...filters, outcomeStatus: event.target.value as RoadmapOutcomeTrendStatus | "" })}><option value="">All outcomes</option>{Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <button type="submit" disabled={loading}>{loading ? "Applying filters…" : "Apply filters"}</button>
      <button type="button" disabled={loading} onClick={() => { setFilters(DEFAULT_FILTERS); void load(DEFAULT_FILTERS); }}>Reset</button>
    </form>

    <p role="status" aria-live="polite">{loading ? "Loading roadmap outcome trend snapshots…" : bundle ? `${bundle.trends.windows.length} trend windows are included.` : "Trend snapshots unavailable."}</p>
    {error ? <p role="alert">{error}</p> : null}

    {bundle ? <>
      <div className="lesson-meta"><span>Trend digest</span><code>{bundle.receipt.trends_sha256}</code></div>
      <div className="lesson-meta"><span>Source report digest</span><code>{bundle.trends.source_report_sha256}</code></div>
      <div className="lesson-meta"><span>Generated</span><span>{new Date(bundle.trends.generated_at).toLocaleString()}</span></div>
      <button type="button" onClick={() => downloadBundle(bundle)}>Export deterministic trend JSON</button>
      <button type="button" onClick={validateBundle}>Validate current trend bundle</button>
      {validation ? <p role="status" aria-live="polite">{validation.valid ? "Trend bundle validation passed." : `Trend bundle validation failed: ${validation.findings.join("; ")}`}</p> : null}
      {bundle.trends.source_excluded_record_count > 0 ? <p role="status">{bundle.trends.source_excluded_record_count} source record(s) were excluded because they failed integrity requirements.</p> : null}
      {bundle.trends.windows.length === 0 ? <p>No roadmap outcome data matches this range.</p> : <section aria-label="Roadmap outcome trend windows">
        {bundle.trends.windows.map((window) => <article key={window.window_start} aria-label={`Trend window beginning ${window.window_start}`}>
          <h3>{new Date(window.window_start).toLocaleDateString()} – {new Date(window.window_end).toLocaleDateString()}</h3>
          <p>{window.action_count} actions · {window.completed_count} completed</p>
          {window.statistics_suppressed ? <p role="status">Rates and cycle-time statistics are hidden until this window has at least {bundle.trends.minimum_window_size} actions.</p> : <p>Completed-action rate: {percentage(window.completed_rate)} · Median completion time: {hours(window.median_completion_hours)}</p>}
          <dl>{Object.entries(window.status_counts).map(([status, count]) => <div key={status}><dt>{STATUS_LABELS[status as RoadmapOutcomeTrendStatus]}</dt><dd>{count}</dd></div>)}</dl>
        </article>)}
      </section>}
      <p>The export excludes project titles, research content, evidence summaries or titles, reflections, prompts, reviewer notes, credentials, private user content, answer keys, and hidden assessment metadata.</p>
    </> : null}
  </section>;
}
