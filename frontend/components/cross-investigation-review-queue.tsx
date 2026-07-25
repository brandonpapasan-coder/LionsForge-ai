"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type {
  CrossInvestigationReviewQueue,
  ReviewQueueReason,
} from "@/lib/investigations";

const reasonOptions: Array<{ value: "all" | ReviewQueueReason; label: string }> = [
  { value: "all", label: "All review reasons" },
  { value: "stale_validation", label: "Stale validation" },
  { value: "missing_validation", label: "Missing validation" },
  { value: "unresolved_contradiction", label: "Unresolved contradiction" },
  { value: "blocked_remediation", label: "Blocked remediation" },
  { value: "remediation_ready_for_review", label: "Ready for review" },
];

export function CrossInvestigationReviewQueuePanel() {
  const [queue, setQueue] = useState<CrossInvestigationReviewQueue | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [reasonFilter, setReasonFilter] = useState<"all" | ReviewQueueReason>("all");
  const [investigationFilter, setInvestigationFilter] = useState("all");
  const [reloadToken, setReloadToken] = useState(0);

  const reload = useCallback(() => {
    setQueue(null);
    setUnavailable(false);
    setReloadToken((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch("/api/investigations/review-queue", {
          cache: "no-store",
          signal: controller.signal,
        });
        if (response.status === 401) { window.location.href = "/login"; return; }
        if (!response.ok) throw new Error();
        const payload = (await response.json()) as CrossInvestigationReviewQueue;
        if (!controller.signal.aborted) setQueue(payload);
      } catch {
        if (!controller.signal.aborted) setUnavailable(true);
      }
    }
    void load();
    return () => controller.abort();
  }, [reloadToken]);

  const investigations = useMemo(() => {
    const values = new Map<number, string>();
    queue?.items.forEach((item) => values.set(item.investigation_id, item.investigation_title));
    return Array.from(values.entries()).sort((left, right) => left[1].localeCompare(right[1]));
  }, [queue]);

  const visibleItems = useMemo(
    () => queue?.items.filter((item) => (
      (reasonFilter === "all" || item.reason_type === reasonFilter)
      && (investigationFilter === "all" || item.investigation_id === Number(investigationFilter))
    )) ?? [],
    [investigationFilter, queue, reasonFilter],
  );

  return <section className="lesson-card" aria-label="Cross-investigation review queue">
    <div className="lesson-meta"><span>private workflow queue</span><span>{queue?.item_count ?? 0} items</span></div>
    <h2>Human review queue</h2>
    <p>This ranking organizes stored workflow conditions only. It is not validation evidence or advice and does not establish truth, confidence, importance, urgency, risk, or resolution.</p>
    {queue === null && !unavailable ? <p role="status">Loading private review queue…</p> : null}
    {unavailable ? <div role="status"><p>The private review queue is temporarily unavailable.</p><button type="button" onClick={reload}>Retry review queue</button></div> : null}
    {queue?.status === "empty" ? <p>No stored investigation items currently require human review.</p> : null}
    {queue?.status === "active" ? <>
      <div className="lesson-grid">
        <label>Review reason<select value={reasonFilter} onChange={(event) => setReasonFilter(event.target.value as "all" | ReviewQueueReason)}>{reasonOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
        <label>Investigation<select value={investigationFilter} onChange={(event) => setInvestigationFilter(event.target.value)}><option value="all">All investigations</option>{investigations.map(([id, title]) => <option key={id} value={id}>{title}</option>)}</select></label>
      </div>
      {visibleItems.length === 0 ? <p>No review queue items match these filters.</p> : null}
      <ol>{visibleItems.map((item) => <li key={item.item_key}>
        <article className="lesson-card" aria-label={`Review queue item ${item.item_key}`}>
          <div className="lesson-meta"><span>workflow priority {item.workflow_priority}</span><span>{item.reason_type.replaceAll("_", " ")}</span></div>
          <h3>{item.investigation_title}</h3>
          <p><strong>Claim:</strong> {item.claim_statement}</p>
          <p>{item.reason}</p>
          <p><strong>Stored inputs:</strong> {item.stored_inputs.join(", ")}</p>
          <p><strong>Stored provenance:</strong> {item.source_tables.map((table, index) => `${table} record ${item.source_record_ids[index] ?? "unknown"}`).join("; ")}</p>
          <time dateTime={item.latest_relevant_at}>{new Date(item.latest_relevant_at).toLocaleString()}</time>
          <p><a href={`#investigation-${item.investigation_id}`}>Open investigation context</a></p>
        </article>
      </li>)}</ol>
    </> : null}
  </section>;
}
