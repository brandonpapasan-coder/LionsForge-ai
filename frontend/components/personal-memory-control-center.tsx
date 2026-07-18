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

type Memory = {
  id: number;
  project_id: number;
  statement: string;
  summary: string;
  category: string;
  status: string;
  confidence: number;
  revision_number: number;
};

type Filters = {
  projectId: string;
  status: string;
  category: string;
  query: string;
};

const emptyFilters: Filters = { projectId: "", status: "", category: "", query: "" };

export function PersonalMemoryControlCenter() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [memory, setMemory] = useState<Memory | null>(null);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [appliedFilters, setAppliedFilters] = useState<Filters>(emptyFilters);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadSummary = useCallback(async () => {
    const response = await fetch("/api/personal-memory/summary", { cache: "no-store" });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
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
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    if (!response.ok) throw new Error("inventory");
    const items = (await response.json()) as Memory[];
    setMemories(items);
    setMemory((selected) => items.find((item) => item.id === selected?.id) ?? null);
  }, []);

  useEffect(() => {
    void Promise.all([loadSummary(), loadInventory(emptyFilters)]).catch(() =>
      setError("Personal memory controls could not be loaded."),
    );
  }, [loadInventory, loadSummary]);

  async function applyFilters() {
    setBusy(true);
    setError(null);
    const next = { ...filters };
    try {
      await loadInventory(next);
      setAppliedFilters(next);
    } catch {
      setError("The memory inventory could not be filtered.");
    } finally {
      setBusy(false);
    }
  }

  async function clearFilters() {
    setFilters(emptyFilters);
    setBusy(true);
    setError(null);
    try {
      await loadInventory(emptyFilters);
      setAppliedFilters(emptyFilters);
    } catch {
      setError("The memory inventory could not be refreshed.");
    } finally {
      setBusy(false);
    }
  }

  async function act(action: "archive" | "restore" | "delete") {
    if (!memory) return;
    if (action === "delete" && !window.confirm("Permanently delete this memory? This cannot be undone.")) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(
        action === "delete"
          ? `/api/personal-memory/${memory.id}`
          : `/api/personal-memory/${memory.id}/${action}`,
        { method: action === "delete" ? "DELETE" : "POST", cache: "no-store" },
      );
      if (!response.ok && response.status !== 204) throw new Error(action);
      const updated = action === "delete" ? null : ((await response.json()) as Memory);
      setMemory(updated);
      await Promise.all([loadSummary(), loadInventory(appliedFilters)]);
    } catch {
      setError(`The ${action} action could not be completed.`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="dashboard-panel" aria-labelledby="personal-memory-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">PERSONAL INTELLIGENCE MEMORY</p>
          <h2 id="personal-memory-title">What LionsForge AI remembers</h2>
        </div>
      </div>

      {error ? <p role="alert">{error}</p> : null}
      {!summary ? (
        <p className="muted">Loading memory controls…</p>
      ) : (
        <>
          <div className="metric-grid" aria-label="Personal memory metrics">
            {[
              ["Total", summary.total_count],
              ["Active", summary.active_count],
              ["Archived", summary.archived_count],
              ["User authored", summary.user_authored_count],
              ["Research generated", summary.research_generated_count],
              ["Revisions", summary.revision_count],
            ].map(([label, value]) => (
              <article className="metric-card" key={String(label)}>
                <span>{label}</span>
                <strong>{value}</strong>
              </article>
            ))}
          </div>
          <p className="muted">Available controls: {summary.available_controls.join(", ")}.</p>
        </>
      )}

      <form
        className="action-list"
        onSubmit={(event) => {
          event.preventDefault();
          void applyFilters();
        }}
        aria-label="Memory inventory filters"
      >
        <label>
          Project ID
          <input
            aria-label="Project ID"
            value={filters.projectId}
            onChange={(event) => setFilters({ ...filters, projectId: event.target.value })}
            inputMode="numeric"
            placeholder="All projects"
          />
        </label>
        <label>
          Status
          <select
            aria-label="Status"
            value={filters.status}
            onChange={(event) => setFilters({ ...filters, status: event.target.value })}
          >
            <option value="">All statuses</option>
            <option value="validated">Validated</option>
            <option value="provisional">Provisional</option>
            <option value="contested">Contested</option>
            <option value="superseded">Superseded</option>
            <option value="archived">Archived</option>
          </select>
        </label>
        <label>
          Category
          <input
            aria-label="Category"
            value={filters.category}
            onChange={(event) => setFilters({ ...filters, category: event.target.value })}
            placeholder="All categories"
          />
        </label>
        <label>
          Search memories
          <input
            aria-label="Search memories"
            value={filters.query}
            onChange={(event) => setFilters({ ...filters, query: event.target.value })}
            placeholder="Statement or summary"
          />
        </label>
        <button type="submit" disabled={busy}>Apply filters</button>
        <button type="button" onClick={() => void clearFilters()} disabled={busy}>Clear filters</button>
      </form>

      <div className="action-list" aria-label="Personal memory inventory">
        {memories.length ? memories.map((item) => (
          <button
            type="button"
            className="action-card"
            key={item.id}
            onClick={() => setMemory(item)}
            aria-pressed={memory?.id === item.id}
          >
            <div>
              <span className={`priority priority-${item.status === "archived" ? "low" : "medium"}`}>
                {item.status}
              </span>
              <h3>{item.summary}</h3>
              <p>{item.statement}</p>
              <p className="muted">Project {item.project_id} · {item.category}</p>
            </div>
          </button>
        )) : <p className="muted">No memories match the current filters.</p>}
      </div>

      {memory ? (
        <article className="action-card" aria-label="Selected memory">
          <div>
            <span className={`priority priority-${memory.status === "archived" ? "low" : "medium"}`}>
              {memory.status}
            </span>
            <h3>{memory.summary}</h3>
            <p>{memory.statement}</p>
            <p className="muted">
              Project {memory.project_id} · {memory.category} · confidence {Math.round(memory.confidence * 100)}% · revision {memory.revision_number}
            </p>
          </div>
          <div className="action-list">
            {memory.status === "archived" ? (
              <button type="button" onClick={() => void act("restore")} disabled={busy}>Restore</button>
            ) : (
              <button type="button" onClick={() => void act("archive")} disabled={busy}>Archive</button>
            )}
            <button type="button" onClick={() => void act("delete")} disabled={busy}>Permanently delete</button>
          </div>
        </article>
      ) : null}
    </section>
  );
}
