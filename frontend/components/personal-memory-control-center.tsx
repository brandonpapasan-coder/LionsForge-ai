"use client";

import { useCallback, useEffect, useState } from "react";

type Summary = {
  project_id: number | null;
  total_count: number;
  active_count: number;
  archived_count: number;
  user_authored_count: number;
  research_generated_count: number;
  revision_count: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  available_controls: string[];
};

type Revision = {
  id: number;
  revision_number: number;
  statement: string;
  summary: string;
  category: string;
  status: string;
  confidence: number;
  created_at: string;
};

type Memory = {
  id: number;
  project_id: number;
  statement: string;
  summary: string;
  category: string;
  status: string;
  confidence: number;
  revision_number: number;
  updated_at?: string;
  revisions?: Revision[];
};

type Filters = { projectId: string; status: string; category: string; query: string };
type RevisionDraft = { statement: string; summary: string; category: string; status: string; confidence: string };

const emptyFilters: Filters = { projectId: "", status: "", category: "", query: "" };

function draftFor(memory: Memory): RevisionDraft {
  return { statement: memory.statement, summary: memory.summary, category: memory.category, status: memory.status, confidence: String(memory.confidence) };
}

function formatTimestamp(value?: string) {
  if (!value) return "Time unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Time unavailable" : date.toLocaleString();
}

export function PersonalMemoryControlCenter() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [memory, setMemory] = useState<Memory | null>(null);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [appliedFilters, setAppliedFilters] = useState<Filters>(emptyFilters);
  const [editing, setEditing] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [draft, setDraft] = useState<RevisionDraft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadSummary = useCallback(async () => {
    const response = await fetch("/api/personal-memory/summary", { cache: "no-store" });
    if (response.status === 401) { window.location.href = "/login"; return; }
    if (!response.ok) throw new Error("summary");
    setSummary((await response.json()) as Summary);
  }, []);

  const loadInventory = useCallback(async (scope: Filters) => {
    const params = new URLSearchParams();
    if (scope.projectId.trim()) params.set("project_id", scope.projectId.trim());
    if (scope.status) params.set("status", scope.status);
    if (scope.category.trim()) params.set("category", scope.category.trim());
    if (scope.query.trim()) params.set("query", scope.query.trim());
    const suffix = params.size ? `?${params.toString()}` : "";
    const response = await fetch(`/api/personal-memory${suffix}`, { cache: "no-store" });
    if (response.status === 401) { window.location.href = "/login"; return; }
    if (!response.ok) throw new Error("inventory");
    const items = (await response.json()) as Memory[];
    setMemories(items);
    setMemory((selected) => items.find((item) => item.id === selected?.id) ?? null);
  }, []);

  useEffect(() => {
    void Promise.all([loadSummary(), loadInventory(emptyFilters)]).catch(() => setError("Personal memory controls could not be loaded."));
  }, [loadInventory, loadSummary]);

  function resetSelectionMode() { setEditing(false); setHistoryOpen(false); setDraft(null); }
  function selectMemory(item: Memory) { setMemory(item); resetSelectionMode(); setError(null); }

  async function applyFilters() {
    setBusy(true); setError(null); const next = { ...filters };
    try { await loadInventory(next); setAppliedFilters(next); resetSelectionMode(); }
    catch { setError("The memory inventory could not be filtered."); }
    finally { setBusy(false); }
  }

  async function clearFilters() {
    setFilters(emptyFilters); setBusy(true); setError(null);
    try { await loadInventory(emptyFilters); setAppliedFilters(emptyFilters); resetSelectionMode(); }
    catch { setError("The memory inventory could not be refreshed."); }
    finally { setBusy(false); }
  }

  async function saveRevision() {
    if (!memory || !draft) return;
    const confidence = Number(draft.confidence);
    if (!Number.isFinite(confidence) || confidence < 0 || confidence > 1) { setError("Confidence must be a number from 0 to 1."); return; }
    setBusy(true); setError(null);
    try {
      const response = await fetch(`/api/personal-memory/${memory.id}`, {
        method: "PATCH", headers: { "content-type": "application/json" },
        body: JSON.stringify({ statement: draft.statement.trim(), summary: draft.summary.trim(), category: draft.category.trim(), status: draft.status, confidence }),
        cache: "no-store",
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) { setError(typeof body.detail === "string" ? body.detail : "The revision could not be saved."); return; }
      setMemory(body as Memory); resetSelectionMode();
      await Promise.all([loadSummary(), loadInventory(appliedFilters)]);
    } catch { setError("The revision could not be saved."); }
    finally { setBusy(false); }
  }

  async function act(action: "archive" | "restore" | "delete") {
    if (!memory) return;
    if (action === "delete" && !window.confirm("Permanently delete this memory? This cannot be undone.")) return;
    setBusy(true); setError(null);
    try {
      const response = await fetch(action === "delete" ? `/api/personal-memory/${memory.id}` : `/api/personal-memory/${memory.id}/${action}`, { method: action === "delete" ? "DELETE" : "POST", cache: "no-store" });
      if (!response.ok && response.status !== 204) throw new Error(action);
      setMemory(action === "delete" ? null : ((await response.json()) as Memory)); resetSelectionMode();
      await Promise.all([loadSummary(), loadInventory(appliedFilters)]);
    } catch { setError(`The ${action} action could not be completed.`); }
    finally { setBusy(false); }
  }

  const orderedRevisions = [...(memory?.revisions ?? [])].sort((a, b) => b.revision_number - a.revision_number);

  return (
    <section className="dashboard-panel" aria-labelledby="personal-memory-title">
      <div className="panel-heading"><div><p className="eyebrow">PERSONAL INTELLIGENCE MEMORY</p><h2 id="personal-memory-title">What LionsForge AI remembers</h2></div></div>
      {error ? <p role="alert">{error}</p> : null}
      {!summary ? <p className="muted">Loading memory controls…</p> : <><div className="metric-grid" aria-label="Personal memory metrics">{[["Total", summary.total_count], ["Active", summary.active_count], ["Archived", summary.archived_count], ["User authored", summary.user_authored_count], ["Research generated", summary.research_generated_count], ["Revisions", summary.revision_count]].map(([label, value]) => <article className="metric-card" key={String(label)}><span>{label}</span><strong>{value}</strong></article>)}</div><p className="muted">Available controls: {summary.available_controls.join(", ")}.</p></>}

      <form className="action-list" onSubmit={(event) => { event.preventDefault(); void applyFilters(); }} aria-label="Memory inventory filters">
        <label>Project ID<input aria-label="Project ID" value={filters.projectId} onChange={(event) => setFilters({ ...filters, projectId: event.target.value })} inputMode="numeric" placeholder="All projects" /></label>
        <label>Status<select aria-label="Status" value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}><option value="">All statuses</option><option value="validated">Validated</option><option value="provisional">Provisional</option><option value="contested">Contested</option><option value="superseded">Superseded</option><option value="archived">Archived</option></select></label>
        <label>Category<input aria-label="Category" value={filters.category} onChange={(event) => setFilters({ ...filters, category: event.target.value })} placeholder="All categories" /></label>
        <label>Search memories<input aria-label="Search memories" value={filters.query} onChange={(event) => setFilters({ ...filters, query: event.target.value })} placeholder="Statement or summary" /></label>
        <button type="submit" disabled={busy}>Apply filters</button><button type="button" onClick={() => void clearFilters()} disabled={busy}>Clear filters</button>
      </form>

      <div className="action-list" aria-label="Personal memory inventory">
        {memories.length ? memories.map((item) => <button type="button" className="action-card" key={item.id} onClick={() => selectMemory(item)} aria-pressed={memory?.id === item.id}><div><span className={`priority priority-${item.status === "archived" ? "low" : "medium"}`}>{item.status}</span><h3>{item.summary}</h3><p>{item.statement}</p><p className="muted">Project {item.project_id} · {item.category}</p></div></button>) : <p className="muted">No memories match the current filters.</p>}
      </div>

      {memory ? <article className="action-card" aria-label="Selected memory">
        {editing && draft ? <form noValidate aria-label="Knowledge record revision editor" onSubmit={(event) => { event.preventDefault(); void saveRevision(); }}>
          <label>Summary<input aria-label="Revision summary" value={draft.summary} onChange={(event) => setDraft({ ...draft, summary: event.target.value })} required /></label>
          <label>Statement<textarea aria-label="Revision statement" value={draft.statement} onChange={(event) => setDraft({ ...draft, statement: event.target.value })} required /></label>
          <label>Category<input aria-label="Revision category" value={draft.category} onChange={(event) => setDraft({ ...draft, category: event.target.value })} required /></label>
          <label>Confidence<input aria-label="Revision confidence" type="number" min="0" max="1" step="0.01" value={draft.confidence} onChange={(event) => setDraft({ ...draft, confidence: event.target.value })} required /></label>
          <label>Status<select aria-label="Revision status" value={draft.status} onChange={(event) => setDraft({ ...draft, status: event.target.value })}><option value="provisional">Provisional</option><option value="validated">Validated</option><option value="contested">Contested</option><option value="archived">Archived</option></select></label>
          <div className="action-list"><button type="submit" disabled={busy}>Save revision</button><button type="button" disabled={busy} onClick={() => { setEditing(false); setDraft(null); setError(null); }}>Cancel</button></div>
        </form> : <>
          <div><span className={`priority priority-${memory.status === "archived" ? "low" : "medium"}`}>{memory.status}</span><h3>{memory.summary}</h3><p>{memory.statement}</p><p className="muted">Project {memory.project_id} · {memory.category} · confidence {Math.round(memory.confidence * 100)}% · revision {memory.revision_number}</p></div>
          <div className="action-list"><button type="button" onClick={() => { setDraft(draftFor(memory)); setEditing(true); setHistoryOpen(false); setError(null); }} disabled={busy || memory.status === "superseded"}>Edit record</button><button type="button" aria-expanded={historyOpen} aria-controls="record-revision-history" onClick={() => setHistoryOpen((open) => !open)} disabled={busy}>{historyOpen ? "Hide revision history" : "View revision history"}</button>{memory.status === "archived" ? <button type="button" onClick={() => void act("restore")} disabled={busy}>Restore</button> : <button type="button" onClick={() => void act("archive")} disabled={busy}>Archive</button>}<button type="button" onClick={() => void act("delete")} disabled={busy}>Permanently delete</button></div>
          {historyOpen ? <section id="record-revision-history" aria-label="Record revision history">
            <h3>Revision history</h3>
            <article className="action-card" aria-label={`Current revision ${memory.revision_number}`}><strong>Current revision {memory.revision_number}</strong><p>{memory.summary}</p><p>{memory.statement}</p><p className="muted">{memory.category} · {memory.status} · confidence {Math.round(memory.confidence * 100)}% · {formatTimestamp(memory.updated_at)}</p></article>
            {orderedRevisions.length ? orderedRevisions.map((revision) => <article className="action-card" key={revision.id} aria-label={`Prior revision ${revision.revision_number}`}><strong>Revision {revision.revision_number}</strong><p>{revision.summary}</p><p>{revision.statement}</p><p className="muted">{revision.category} · {revision.status} · confidence {Math.round(revision.confidence * 100)}% · {formatTimestamp(revision.created_at)}</p></article>) : <p className="muted">No prior revisions are available.</p>}
          </section> : null}
        </>}
      </article> : null}
    </section>
  );
}
