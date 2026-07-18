"use client";

import { useCallback, useEffect, useState } from "react";

type EscalationState = "fresh" | "aging" | "overdue" | "critical";
type EscalationItem = {
  follow_up_id: number;
  project_id: number;
  evidence_id: number;
  action_key: string;
  governing_rule: string;
  status: string;
  priority: "urgent" | "high" | "normal" | "low";
  escalation_state: EscalationState;
  age_days: number;
  idle_days: number;
  due_at: string | null;
  days_overdue: number;
  next_escalation_at: string | null;
  escalation_reason: string;
  recommended_owner_action: string;
};
type Inventory = {
  project_id: number | null;
  escalation_state: EscalationState | null;
  total: number;
  by_state: Record<EscalationState, number>;
  items: EscalationItem[];
  disclaimer: string;
};

export function PersonalMemoryEvidenceRemediationEscalations() {
  const [projectId, setProjectId] = useState("");
  const [state, setState] = useState("");
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (project: string, escalationState: string) => {
    const params = new URLSearchParams();
    if (project.trim()) params.set("project_id", project.trim());
    if (escalationState) params.set("escalation_state", escalationState);
    const suffix = params.size ? `?${params.toString()}` : "";
    const response = await fetch(`/api/personal-memory/evidence-remediation/escalations${suffix}`, { cache: "no-store" });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Escalation inventory could not be loaded.");
    setInventory(body as Inventory);
  }, []);

  useEffect(() => {
    void load("", "").catch(() => setError("Evidence remediation escalations could not be loaded."));
  }, [load]);

  async function applyFilters() {
    setBusy(true);
    setError(null);
    try {
      await load(projectId, state);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Escalation inventory could not be loaded.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="dashboard-panel" aria-labelledby="remediation-escalations-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">REMEDIATION ESCALATIONS</p>
          <h2 id="remediation-escalations-title">Keep unresolved evidence work visible</h2>
        </div>
      </div>
      {error ? <p role="alert">{error}</p> : null}
      <form
        className="action-list"
        aria-label="Evidence remediation escalation filters"
        onSubmit={(event) => {
          event.preventDefault();
          void applyFilters();
        }}
      >
        <label>
          Project ID
          <input aria-label="Escalation project ID" value={projectId} onChange={(event) => setProjectId(event.target.value)} inputMode="numeric" placeholder="All projects" />
        </label>
        <label>
          Escalation state
          <select aria-label="Escalation state" value={state} onChange={(event) => setState(event.target.value)}>
            <option value="">All states</option>
            <option value="critical">Critical</option>
            <option value="overdue">Overdue</option>
            <option value="aging">Aging</option>
            <option value="fresh">Fresh</option>
          </select>
        </label>
        <button type="submit" disabled={busy}>{busy ? "Applying…" : "Apply filters"}</button>
      </form>
      {!inventory ? <p className="muted">Loading remediation escalations…</p> : (
        <>
          <div className="metric-grid" aria-label="Evidence remediation escalation metrics">
            {(["critical", "overdue", "aging", "fresh"] as EscalationState[]).map((item) => (
              <article className="metric-card" key={item}><span>{item}</span><strong>{inventory.by_state[item]}</strong></article>
            ))}
          </div>
          <div className="action-list" aria-label="Evidence remediation escalation inventory">
            {inventory.items.length ? inventory.items.map((item) => (
              <article className="action-card" key={item.follow_up_id}>
                <div>
                  <span className={`priority priority-${item.escalation_state === "critical" || item.escalation_state === "overdue" ? "high" : item.escalation_state === "aging" ? "medium" : "low"}`}>{item.escalation_state}</span>
                  <h3>Follow-up #{item.follow_up_id} · {item.priority}</h3>
                  <p>{item.escalation_reason}</p>
                  <p>{item.recommended_owner_action}</p>
                  <p className="muted">Project {item.project_id} · age {item.age_days} day(s) · idle {item.idle_days} day(s){item.days_overdue ? ` · ${item.days_overdue} day(s) overdue` : ""}</p>
                  {item.next_escalation_at ? <p className="muted">Next escalation: {new Date(item.next_escalation_at).toLocaleString()}</p> : null}
                </div>
              </article>
            )) : <p className="muted">No active remediation follow-ups match the current filters.</p>}
          </div>
          <p className="muted">{inventory.disclaimer}</p>
        </>
      )}
    </section>
  );
}
