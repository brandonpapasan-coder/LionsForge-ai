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
  statement: string;
  summary: string;
  category: string;
  status: string;
  confidence: number;
  revision_number: number;
};

export function PersonalMemoryControlCenter() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [memoryId, setMemoryId] = useState("");
  const [memory, setMemory] = useState<Memory | null>(null);
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

  useEffect(() => {
    void loadSummary().catch(() => setError("Personal memory controls could not be loaded."));
  }, [loadSummary]);

  async function inspect() {
    if (!memoryId.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/personal-memory/${encodeURIComponent(memoryId.trim())}`, {
        cache: "no-store",
      });
      if (!response.ok) throw new Error("inspect");
      setMemory((await response.json()) as Memory);
    } catch {
      setMemory(null);
      setError("That memory could not be inspected.");
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
      if (action === "delete") {
        setMemory(null);
        setMemoryId("");
      } else {
        setMemory((await response.json()) as Memory);
      }
      await loadSummary();
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
          <p className="muted">
            Available controls: {summary.available_controls.join(", ")}.
          </p>
        </>
      )}

      <div className="action-list">
        <label>
          Memory ID
          <input
            value={memoryId}
            onChange={(event) => setMemoryId(event.target.value)}
            inputMode="numeric"
            placeholder="Enter a memory ID"
          />
        </label>
        <button type="button" onClick={() => void inspect()} disabled={busy || !memoryId.trim()}>
          Inspect memory
        </button>
      </div>

      {memory ? (
        <article className="action-card">
          <div>
            <span className={`priority priority-${memory.status === "archived" ? "low" : "medium"}`}>
              {memory.status}
            </span>
            <h3>{memory.summary}</h3>
            <p>{memory.statement}</p>
            <p className="muted">
              {memory.category} · confidence {Math.round(memory.confidence * 100)}% · revision {memory.revision_number}
            </p>
          </div>
          <div className="action-list">
            {memory.status === "archived" ? (
              <button type="button" onClick={() => void act("restore")} disabled={busy}>Restore</button>
            ) : (
              <button type="button" onClick={() => void act("archive")} disabled={busy}>Archive</button>
            )}
            <button type="button" onClick={() => void act("delete")} disabled={busy}>
              Permanently delete
            </button>
          </div>
        </article>
      ) : null}
    </section>
  );
}
