"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import type { RemediationProgressLedger, RemediationProgressStatus } from "@/lib/investigations";

const statuses: RemediationProgressStatus[] = ["not_started", "in_progress", "blocked", "ready_for_review", "dismissed"];

export function RemediationProgressLedgerPanel({ investigationId }: { investigationId: number }) {
  const [ledger, setLedger] = useState<RemediationProgressLedger | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [savingClaimId, setSavingClaimId] = useState<number | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const reload = useCallback(() => {
    setLedger(null);
    setUnavailable(false);
    setReloadToken((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch(`/api/investigations/${investigationId}/remediation-progress`, { cache: "no-store", signal: controller.signal });
        if (response.status === 401) { window.location.href = "/login"; return; }
        if (!response.ok) throw new Error();
        const payload = (await response.json()) as RemediationProgressLedger;
        if (!controller.signal.aborted) setLedger(payload);
      } catch {
        if (!controller.signal.aborted) setUnavailable(true);
      }
    }
    void load();
    return () => controller.abort();
  }, [investigationId, reloadToken]);

  async function save(event: FormEvent<HTMLFormElement>, claimId: number) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSavingClaimId(claimId);
    try {
      const response = await fetch(`/api/investigations/${investigationId}/remediation-progress/${claimId}`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ status: form.get("status"), notes: form.get("notes") }),
      });
      if (response.status === 401) { window.location.href = "/login"; return; }
      if (!response.ok) throw new Error();
      setLedger((await response.json()) as RemediationProgressLedger);
    } catch {
      setUnavailable(true);
    } finally {
      setSavingClaimId(null);
    }
  }

  return <section aria-label="Remediation progress ledger">
    <h4>Remediation progress ledger</h4>
    <p>Statuses and notes are user-authored workflow records. They do not change validation, remediation priority, truth, completion, or resolution.</p>
    {ledger === null && !unavailable ? <p role="status">Loading remediation progress…</p> : null}
    {unavailable ? <div role="status"><p>The remediation progress ledger is temporarily unavailable.</p><button type="button" onClick={reload}>Retry progress ledger</button></div> : null}
    {ledger?.status === "empty" ? <p>No remediation progress has been recorded yet. Use the current remediation actions to begin tracking work.</p> : null}
    {ledger?.entries.map((entry) => <article className="lesson-card" key={entry.claim_id} aria-label={`${entry.statement}: remediation progress`}>
      <div className="lesson-meta"><span>{entry.authorship.replaceAll("_", " ")}</span><span>{entry.is_stale ? "stale record" : "current record"}</span></div>
      <h5>{entry.statement}</h5>
      {entry.is_stale ? <div role="status"><strong>Progress record needs review</strong><ul>{entry.stale_reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></div> : null}
      <p><strong>Saved action:</strong> {entry.action_type_snapshot.replaceAll("_", " ")} · priority {entry.priority_snapshot}</p>
      {entry.current_action ? <div><p><strong>Current action:</strong> {entry.current_action.action_type.replaceAll("_", " ")} · priority {entry.current_action.priority}</p><p>{entry.current_action.rationale}</p><ul>{entry.current_action.completion_criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}</ul></div> : <p>No current deterministic remediation action exists for this claim. The historical progress record is preserved.</p>}
      {entry.current_action ? <form onSubmit={(event) => void save(event, entry.claim_id)}>
        <label>Workflow status<select name="status" defaultValue={entry.status}>{statuses.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select></label>
        <label>Researcher note<textarea name="notes" maxLength={8000} defaultValue={entry.notes ?? ""} /></label>
        <button type="submit" disabled={savingClaimId === entry.claim_id}>{savingClaimId === entry.claim_id ? "Saving…" : "Save progress"}</button>
      </form> : null}
      <time dateTime={entry.updated_at}>Updated {new Date(entry.updated_at).toLocaleString()}</time>
    </article>)}
  </section>;
}
