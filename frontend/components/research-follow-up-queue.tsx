"use client";

import { useEffect, useMemo, useState } from "react";

import type { ResearchProject } from "@/lib/research";

type Status = "open" | "acknowledged" | "in_progress" | "blocked" | "deferred" | "resolved" | "dismissed";
type Priority = "low" | "normal" | "high" | "urgent";
type Action = {
  id: number; project_id: number; evidence_id: number; impact_level: string; governing_rule: string;
  reason: string; action_text: string; supporting_event_ids: string[]; status: Status; priority: Priority;
  due_at: string | null; owner_notes: string | null; resolution_notes: string | null; resolved_at: string | null;
  overdue: boolean; urgency_rank: number; history: { id: number; previous_status: Status; new_status: Status; note: string | null; created_at: string }[];
};
type Queue = { project_id: number; total: number; overdue: number; blocked: number; actions: Action[]; disclaimer: string };

const statuses: Status[] = ["open", "acknowledged", "in_progress", "blocked", "deferred", "resolved", "dismissed"];
const priorities: Priority[] = ["urgent", "high", "normal", "low"];

export function ResearchFollowUpQueue() {
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [queue, setQueue] = useState<Queue | null>(null);
  const [status, setStatus] = useState<"all" | Status>("all");
  const [priority, setPriority] = useState<"all" | Priority>("all");
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetch("/api/research-projects", { cache: "no-store" }).then(async (response) => {
      if (response.status === 401) { window.location.href = "/login"; return; }
      if (!response.ok) throw new Error();
      const body = await response.json() as ResearchProject[];
      setProjects(body); setProjectId(body[0]?.id ?? null);
    }).catch(() => setError("Research projects could not be loaded.")).finally(() => setLoading(false));
  }, []);

  async function loadQueue(id: number) {
    const params = new URLSearchParams();
    if (status !== "all") params.set("status", status);
    if (priority !== "all") params.set("priority", priority);
    if (overdueOnly) params.set("overdue_only", "true");
    const response = await fetch(`/api/research-follow-up-tracker/projects/${id}?${params}`, { cache: "no-store" });
    if (response.status === 401) { window.location.href = "/login"; return; }
    if (!response.ok) throw new Error();
    setQueue(await response.json() as Queue);
  }

  useEffect(() => {
    if (!projectId) return;
    setError(null);
    void loadQueue(projectId).catch(() => setError("The follow-up queue could not be loaded."));
  }, [projectId, status, priority, overdueOnly]);

  async function updateAction(action: Action, patch: Record<string, unknown>) {
    if (!window.confirm("Apply this audited follow-up action update?")) return;
    const response = await fetch(`/api/research-follow-up-tracker/actions/${action.id}`, {
      method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ ...patch, confirmed: true }),
    });
    if (!response.ok) { setError("The follow-up action could not be updated."); return; }
    if (projectId) await loadQueue(projectId);
  }

  const active = useMemo(() => queue?.actions ?? [], [queue]);
  if (loading) return <section className="dashboard-state">Loading follow-up queue…</section>;
  if (!projectId) return <section className="dashboard-state">Create a research project to begin tracking follow-up actions.</section>;

  return <section className="research-provenance-section">
    <div className="research-section-heading"><div><p className="eyebrow">RESEARCH WORKSPACE</p><h1>Follow-up action tracker</h1><p className="muted">Manage review workflow without changing or approving underlying evidence.</p></div></div>
    {error ? <p role="alert" className="form-message">{error}</p> : null}
    <section className="dashboard-panel"><div className="form-grid">
      <label>Project<select aria-label="Follow-up project" value={projectId} onChange={(event) => setProjectId(Number(event.target.value))}>{projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}</select></label>
      <label>Status<select aria-label="Follow-up status filter" value={status} onChange={(event) => setStatus(event.target.value as typeof status)}><option value="all">All statuses</option>{statuses.map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}</select></label>
      <label>Priority<select aria-label="Follow-up priority filter" value={priority} onChange={(event) => setPriority(event.target.value as typeof priority)}><option value="all">All priorities</option>{priorities.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
      <label><input type="checkbox" checked={overdueOnly} onChange={(event) => setOverdueOnly(event.target.checked)} /> Overdue only</label>
    </div></section>
    {queue ? <div className="metric-grid"><article><strong>{queue.total}</strong><span>Total</span></article><article><strong>{queue.overdue}</strong><span>Overdue</span></article><article><strong>{queue.blocked}</strong><span>Blocked</span></article></div> : null}
    <section className="dashboard-panel"><div className="panel-heading"><div><p className="eyebrow">DETERMINISTIC URGENCY ORDER</p><h2>Action queue</h2><p className="muted">{queue?.disclaimer}</p></div></div>
      <div className="activity-list">{active.map((action) => <article className="activity-card" key={action.id}><span>{action.overdue ? "OVERDUE" : action.priority.toUpperCase()}</span><div>
        <strong>{action.status.replaceAll("_", " ")} · evidence {action.evidence_id}</strong><p>{action.reason}</p><p><strong>Action:</strong> {action.action_text}</p><p><strong>Rule:</strong> {action.governing_rule} · <strong>Events:</strong> {action.supporting_event_ids.join(", ")}</p><p><strong>Due:</strong> {action.due_at ? new Date(action.due_at).toLocaleString() : "Not set"}</p>
        <div><button type="button" onClick={() => void updateAction(action, { status: "in_progress", note: "Work started." })}>Start</button><button type="button" onClick={() => void updateAction(action, { status: "blocked", note: "Blocked pending user review." })}>Block</button><button type="button" onClick={() => void updateAction(action, { status: "deferred", note: "Deferred by owner." })}>Defer</button><button type="button" onClick={() => void updateAction(action, { status: "resolved", resolution_notes: window.prompt("Resolution notes are required:") ?? "" })}>Resolve</button>{["resolved", "dismissed"].includes(action.status) ? <button type="button" onClick={() => void updateAction(action, { status: "open", note: "Reopened by owner." })}>Reopen</button> : null}</div>
        {action.history.length ? <details><summary>Audit history ({action.history.length})</summary>{action.history.map((item) => <p key={item.id}>{item.previous_status} → {item.new_status}{item.note ? ` · ${item.note}` : ""}</p>)}</details> : null}
      </div></article>)}</div>
      {!active.length ? <p>No follow-up actions match the selected filters.</p> : null}
    </section>
  </section>;
}
