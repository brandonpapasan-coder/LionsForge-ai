"use client";

import { useEffect, useState } from "react";

type Metric = { key: string; label: string; count: number; action_ids: number[] };
type TraceItem = {
  action_id: number;
  evidence_id: number;
  impact_level: "high_attention" | "review_required" | "informational";
  governing_rule: string;
  status: "open" | "acknowledged" | "deferred" | "resolved";
  reason: string;
  action_text: string;
  supporting_event_ids: string[];
  age_days: number;
  age_bucket: string;
  overdue: boolean;
  reopen_count: number;
};
type Dashboard = {
  project_id: number;
  total_actions: number;
  status_metrics: Metric[];
  impact_metrics: Metric[];
  rule_metrics: Metric[];
  aging_metrics: Metric[];
  overdue_count: number;
  repeatedly_reopened_count: number;
  throughput: { resolved_transitions: number; reopened_transitions: number; net_resolved: number; window_days: number; action_ids: number[] };
  trace_items: TraceItem[];
  disclaimer: string;
};

export function ResearchGovernanceDashboard({ projectId }: { projectId: number }) {
  const [days, setDays] = useState(30);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setError(null);
      try {
        const response = await fetch(`/api/research-governance-dashboard/${projectId}?days=${days}`, { cache: "no-store", signal: controller.signal });
        if (response.status === 401) { window.location.href = "/login"; return; }
        if (!response.ok) { setError("The research governance dashboard could not be loaded."); return; }
        setDashboard((await response.json()) as Dashboard);
      } catch (requestError) {
        if (!(requestError instanceof DOMException && requestError.name === "AbortError")) setError("The research governance dashboard is unavailable.");
      }
    }
    void load();
    return () => controller.abort();
  }, [projectId, days]);

  return <section className="dashboard-panel" aria-labelledby="governance-dashboard-title">
    <div className="panel-heading"><div><p className="eyebrow">RESEARCH GOVERNANCE</p><h3 id="governance-dashboard-title">Review dashboard</h3><p className="muted">{dashboard?.disclaimer ?? "Loading governance workflow metrics…"}</p></div><label>Time range<select aria-label="Governance time range" value={days} onChange={(event) => setDays(Number(event.target.value))}><option value={7}>7 days</option><option value={30}>30 days</option><option value={90}>90 days</option><option value={365}>365 days</option></select></label></div>
    {error ? <p role="alert" className="form-message">{error}</p> : null}
    {dashboard ? <>
      <div className="metric-grid"><article><strong>{dashboard.total_actions}</strong><span>Total actions</span></article><article><strong>{dashboard.overdue_count}</strong><span>Overdue</span></article><article><strong>{dashboard.repeatedly_reopened_count}</strong><span>Repeatedly reopened</span></article><article><strong>{dashboard.throughput.net_resolved}</strong><span>Net resolved</span></article></div>
      <div className="activity-list">
        {[...dashboard.status_metrics, ...dashboard.impact_metrics, ...dashboard.aging_metrics].map((metric) => <article className="activity-card" key={`${metric.key}-${metric.label}`}><span>{metric.count}</span><div><strong>{metric.label}</strong><p>Actions: {metric.action_ids.length ? metric.action_ids.join(", ") : "none"}</p></div></article>)}
      </div>
      <p><strong>Throughput:</strong> {dashboard.throughput.resolved_transitions} resolved · {dashboard.throughput.reopened_transitions} reopened across {dashboard.throughput.window_days} days.</p>
      <div className="activity-list">{dashboard.trace_items.map((item) => <article className="activity-card" key={item.action_id}><span>{item.overdue ? "OVERDUE" : item.status.toUpperCase()}</span><div><strong>Action {item.action_id} · evidence {item.evidence_id}</strong><p>{item.reason}</p><p><strong>Rule:</strong> {item.governing_rule} · <strong>Impact:</strong> {item.impact_level.replaceAll("_", " ")}</p><p><strong>Age:</strong> {item.age_days} days · <strong>Reopened:</strong> {item.reopen_count}</p><p><strong>Events:</strong> {item.supporting_event_ids.join(", ") || "none"}</p><details><summary>Review action</summary><p>{item.action_text}</p></details></div></article>)}</div>
    </> : null}
  </section>;
}
