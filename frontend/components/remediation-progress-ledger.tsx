"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import type {
  RemediationProgressHistory,
  RemediationProgressLedger,
  RemediationProgressStatus,
} from "@/lib/investigations";

const statuses: RemediationProgressStatus[] = ["not_started", "in_progress", "blocked", "ready_for_review", "dismissed"];

type HistoryState = { loading: boolean; unavailable: boolean; data: RemediationProgressHistory | null };

export function RemediationProgressLedgerPanel({ investigationId }: { investigationId: number }) {
  const [ledger, setLedger] = useState<RemediationProgressLedger | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [savingClaimId, setSavingClaimId] = useState<number | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [historyByClaim, setHistoryByClaim] = useState<Record<number, HistoryState>>({});

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

  async function loadHistory(claimId: number) {
    setHistoryByClaim((current) => ({ ...current, [claimId]: { loading: true, unavailable: false, data: null } }));
    try {
      const response = await fetch(`/api/investigations/${investigationId}/remediation-progress/${claimId}/history`, { cache: "no-store" });
      if (response.status === 401) { window.location.href = "/login"; return; }
      if (!response.ok) throw new Error();
      const data = (await response.json()) as RemediationProgressHistory;
      setHistoryByClaim((current) => ({ ...current, [claimId]: { loading: false, unavailable: false, data } }));
    } catch {
      setHistoryByClaim((current) => ({ ...current, [claimId]: { loading: false, unavailable: true, data: null } }));
    }
  }

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
      if (historyByClaim[claimId]?.data) await loadHistory(claimId);
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
    {ledger?.entries.map((entry) => {
      const history = historyByClaim[entry.claim_id];
      return <article className="lesson-card" key={entry.claim_id} aria-label={`${entry.statement}: remediation progress`}>
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
        <details onToggle={(event) => { if (event.currentTarget.open && !history) void loadHistory(entry.claim_id); }}>
          <summary>Progress history</summary>
          <p>Append-only user-authored workflow history. It is not validation evidence and does not establish completion or resolution.</p>
          {history?.loading ? <p role="status">Loading progress history…</p> : null}
          {history?.unavailable ? <div role="status"><p>Progress history is temporarily unavailable.</p><button type="button" onClick={() => void loadHistory(entry.claim_id)}>Retry progress history</button></div> : null}
          {history?.data?.status === "empty" ? <p>No history events have been recorded for this claim.</p> : null}
          {history?.data?.events.map((event) => <article key={event.event_id} aria-label={`History event ${event.event_id}`}>
            <p><strong>{event.status.replaceAll("_", " ")}</strong> · {event.action_type_snapshot.replaceAll("_", " ")} · priority {event.priority_snapshot}</p>
            <p>{event.notes ?? "No researcher note recorded."}</p>
            <time dateTime={event.recorded_at}>{new Date(event.recorded_at).toLocaleString()}</time>
          </article>)}
        </details>
      </article>;
    })}
  </section>;
}
