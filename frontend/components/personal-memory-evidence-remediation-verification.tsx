"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type InventoryItem = { memory_id: number; summary: string };
type Inventory = { items: InventoryItem[] };
type Criterion = { criterion: string; passed: boolean; explanation: string; supporting_evidence_ids: number[] };
type Action = {
  action_key: string;
  action_type: string;
  follow_up_id: number | null;
  follow_up_status: string | null;
  status: "unresolved" | "partially_satisfied" | "ready_for_resolution";
  passed_count: number;
  total_count: number;
  criteria: Criterion[];
};
type Verification = {
  memory_id: number;
  project_id: number;
  total_actions: number;
  ready_for_resolution_count: number;
  actions: Action[];
};

function isAbortError(error: unknown) {
  return error instanceof DOMException && error.name === "AbortError";
}

export function PersonalMemoryEvidenceRemediationVerification() {
  const recordsRef = useRef<InventoryItem[]>([]);
  const loadingRecordsRef = useRef<Promise<InventoryItem[]> | null>(null);
  const inventoryAbortRef = useRef<AbortController | null>(null);
  const verificationAbortRef = useRef<AbortController | null>(null);
  const [selectedMemoryId, setSelectedMemoryId] = useState<number | null>(null);
  const [verification, setVerification] = useState<Verification | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadVerification = useCallback(async (memoryId: number) => {
    verificationAbortRef.current?.abort();
    const controller = new AbortController();
    verificationAbortRef.current = controller;

    try {
      const response = await fetch(`/api/personal-memory/${memoryId}/evidence-remediation/verification`, {
        cache: "no-store",
        signal: controller.signal,
      });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Remediation verification could not be loaded.");
      if (!controller.signal.aborted) setVerification(body as Verification);
    } finally {
      if (verificationAbortRef.current === controller) verificationAbortRef.current = null;
    }
  }, []);

  const loadRecords = useCallback(async () => {
    if (recordsRef.current.length) return recordsRef.current;
    if (!loadingRecordsRef.current) {
      const controller = new AbortController();
      inventoryAbortRef.current = controller;
      loadingRecordsRef.current = fetch("/api/personal-memory/evidence-health", {
        cache: "no-store",
        signal: controller.signal,
      })
        .then(async (response) => {
          if (response.status === 401) {
            window.location.href = "/login";
            return [];
          }
          if (!response.ok) throw new Error("inventory");
          const items = ((await response.json()) as Inventory).items;
          if (!controller.signal.aborted) recordsRef.current = items;
          return items;
        })
        .finally(() => {
          if (inventoryAbortRef.current === controller) inventoryAbortRef.current = null;
          loadingRecordsRef.current = null;
        });
    }
    return loadingRecordsRef.current;
  }, []);

  const selectFromText = useCallback(async (text: string) => {
    try {
      const records = await loadRecords();
      const selected = records.find((item) => text.includes(item.summary));
      if (!selected) {
        setError("The selected saved record could not be matched for remediation verification.");
        return;
      }
      setSelectedMemoryId(selected.memory_id);
      setVerification(null);
      setError(null);
      await loadVerification(selected.memory_id);
    } catch (requestError) {
      if (isAbortError(requestError)) return;
      setError(requestError instanceof Error ? requestError.message : "Remediation verification could not be loaded.");
    }
  }, [loadRecords, loadVerification]);

  useEffect(() => {
    function onClick(event: Event) {
      const target = (event.target as Element | null)?.closest('[aria-label="Personal memory inventory"] button');
      const text = target?.textContent ?? "";
      if (text) void selectFromText(text);
    }
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, [selectFromText]);

  useEffect(() => () => {
    inventoryAbortRef.current?.abort();
    verificationAbortRef.current?.abort();
  }, []);

  async function resolve(action: Action) {
    if (selectedMemoryId === null || action.status !== "ready_for_resolution" || action.follow_up_id === null) return;
    const resolutionNotes = (notes[action.action_key] ?? "").trim();
    if (!resolutionNotes) {
      setError("Resolution notes are required.");
      return;
    }
    if (!window.confirm("Resolve this verified research follow-up?")) return;
    setBusyKey(action.action_key);
    setError(null);
    try {
      const response = await fetch(
        `/api/personal-memory/${selectedMemoryId}/evidence-remediation/verification/resolve`,
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ action_key: action.action_key, confirmed: true, resolution_notes: resolutionNotes }),
          cache: "no-store",
        },
      );
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Verified follow-up could not be resolved.");
      await loadVerification(selectedMemoryId);
    } catch (requestError) {
      if (isAbortError(requestError)) return;
      setError(requestError instanceof Error ? requestError.message : "Verified follow-up could not be resolved.");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <section className="dashboard-panel" aria-labelledby="evidence-remediation-verification-title">
      <div className="panel-heading"><div><p className="eyebrow">REMEDIATION VERIFICATION</p><h2 id="evidence-remediation-verification-title">Verify completion before resolution</h2></div></div>
      {error ? <p role="alert">{error}</p> : null}
      {selectedMemoryId === null ? <p className="muted">Select a saved record to verify its remediation criteria.</p> : !verification ? <p className="muted">Loading remediation verification…</p> : (
        <div className="action-list" aria-label="Evidence remediation verification actions">
          <p>Record {verification.memory_id} · project {verification.project_id} · {verification.ready_for_resolution_count}/{verification.total_actions} action(s) ready for resolution</p>
          {verification.actions.length ? verification.actions.map((action) => (
            <article className="action-card" key={action.action_key}>
              <div>
                <span className={`priority priority-${action.status === "ready_for_resolution" ? "low" : action.status === "partially_satisfied" ? "medium" : "high"}`}>{action.status.replaceAll("_", " ")}</span>
                <h3>{action.action_type.replaceAll("_", " ")}</h3>
                <p>{action.passed_count}/{action.total_count} completion criteria passed.</p>
                <ul>{action.criteria.map((criterion) => <li key={criterion.criterion}><strong>{criterion.passed ? "Passed" : "Not passed"}:</strong> {criterion.criterion} — {criterion.explanation}{criterion.supporting_evidence_ids.length ? ` Evidence IDs: ${criterion.supporting_evidence_ids.join(", ")}.` : ""}</li>)}</ul>
              </div>
              {action.follow_up_status === "resolved" ? <span role="status">Follow-up #{action.follow_up_id} resolved</span> : action.status === "ready_for_resolution" && action.follow_up_id !== null ? (
                <div>
                  <label>Resolution notes<textarea aria-label={`Resolution notes for ${action.action_type}`} value={notes[action.action_key] ?? ""} onChange={(event) => setNotes({ ...notes, [action.action_key]: event.target.value })} /></label>
                  <button type="button" disabled={busyKey !== null} onClick={() => void resolve(action)}>{busyKey === action.action_key ? "Resolving…" : "Resolve verified follow-up"}</button>
                </div>
              ) : <span className="muted">{action.follow_up_id === null ? "Create the research follow-up before resolution." : "All criteria must pass before resolution."}</span>}
            </article>
          )) : <p className="muted">No remediation actions require verification.</p>}
        </div>
      )}
    </section>
  );
}
