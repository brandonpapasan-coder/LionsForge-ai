"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type InventoryItem = { memory_id: number; summary: string };
type Inventory = { items: InventoryItem[] };

type Health = {
  classification: "strong" | "adequate" | "weak" | "contested" | "unavailable" | "unsupported";
};

type RemediationAction = {
  action_key: string;
  action_type: string;
  priority: "urgent" | "high" | "normal" | "low";
  rationale: string;
  action_text: string;
  related_evidence_ids: number[];
  completion_criteria: string[];
  existing_follow_up_id: number | null;
};

type RemediationPlan = {
  memory_id: number;
  project_id: number;
  health: Health;
  total_actions: number;
  open_follow_up_count: number;
  actions: RemediationAction[];
};

export function PersonalMemoryEvidenceRemediation() {
  const recordsRef = useRef<InventoryItem[]>([]);
  const pendingSelectionRef = useRef<string | null>(null);
  const [selectedMemoryId, setSelectedMemoryId] = useState<number | null>(null);
  const [plan, setPlan] = useState<RemediationPlan | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadPlan = useCallback(async (memoryId: number) => {
    const response = await fetch(`/api/personal-memory/${memoryId}/evidence-remediation`, { cache: "no-store" });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Remediation plan could not be loaded.");
    setPlan(body as RemediationPlan);
  }, []);

  const selectFromText = useCallback((text: string) => {
    const selected = recordsRef.current.find((item) => text.includes(item.summary));
    if (!selected) return false;
    pendingSelectionRef.current = null;
    setSelectedMemoryId(selected.memory_id);
    setPlan(null);
    setError(null);
    void loadPlan(selected.memory_id).catch((requestError) => {
      setError(requestError instanceof Error ? requestError.message : "Remediation plan could not be loaded.");
    });
    return true;
  }, [loadPlan]);

  useEffect(() => {
    async function loadRecords() {
      try {
        const response = await fetch("/api/personal-memory/evidence-health", { cache: "no-store" });
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) throw new Error("inventory");
        recordsRef.current = ((await response.json()) as Inventory).items;
        if (pendingSelectionRef.current) selectFromText(pendingSelectionRef.current);
      } catch {
        setError("Evidence remediation records could not be loaded.");
      }
    }
    void loadRecords();
  }, [selectFromText]);

  useEffect(() => {
    function onClick(event: Event) {
      const target = (event.target as Element | null)?.closest('[aria-label="Personal memory inventory"] button');
      const text = target?.textContent ?? "";
      if (!text) return;
      if (!selectFromText(text)) pendingSelectionRef.current = text;
    }

    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, [selectFromText]);

  async function createFollowUp(action: RemediationAction) {
    if (action.existing_follow_up_id !== null) return;
    if (!window.confirm("Create this research evidence follow-up?")) return;
    setBusyKey(action.action_key);
    setError(null);
    try {
      const response = await fetch(
        `/api/personal-memory/${selectedMemoryId}/evidence-remediation/follow-ups`,
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ action_key: action.action_key, confirmed: true }),
          cache: "no-store",
        },
      );
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Research follow-up could not be created.");
      if (selectedMemoryId !== null) await loadPlan(selectedMemoryId);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Research follow-up could not be created.");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <section className="dashboard-panel" aria-labelledby="evidence-remediation-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">EVIDENCE REMEDIATION</p>
          <h2 id="evidence-remediation-title">Turn evidence gaps into research actions</h2>
        </div>
      </div>
      {error ? <p role="alert">{error}</p> : null}
      {selectedMemoryId === null ? (
        <p className="muted">Select a saved record to see its evidence remediation plan.</p>
      ) : !plan ? (
        <p className="muted">Loading remediation plan…</p>
      ) : (
        <>
          <p>
            Record {plan.memory_id} · project {plan.project_id} · {plan.health.classification} evidence health · {plan.open_follow_up_count} open follow-up(s)
          </p>
          <div className="action-list" aria-label="Evidence remediation actions">
            {plan.actions.length ? plan.actions.map((action) => (
              <article className="action-card" key={action.action_key}>
                <div>
                  <span className={`priority priority-${action.priority === "urgent" || action.priority === "high" ? "high" : action.priority === "normal" ? "medium" : "low"}`}>{action.priority}</span>
                  <h3>{action.action_type.replaceAll("_", " ")}</h3>
                  <p>{action.rationale}</p>
                  <p>{action.action_text}</p>
                  {action.related_evidence_ids.length ? <p className="muted">Evidence IDs: {action.related_evidence_ids.join(", ")}</p> : null}
                  <strong>Completion criteria</strong>
                  <ul>{action.completion_criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}</ul>
                </div>
                {action.existing_follow_up_id !== null ? (
                  <span role="status">Follow-up #{action.existing_follow_up_id} already open</span>
                ) : (
                  <button type="button" disabled={busyKey !== null} onClick={() => void createFollowUp(action)}>
                    {busyKey === action.action_key ? "Creating follow-up…" : "Create research follow-up"}
                  </button>
                )}
              </article>
            )) : <p className="muted">No evidence remediation actions are currently required.</p>}
          </div>
        </>
      )}
    </section>
  );
}
