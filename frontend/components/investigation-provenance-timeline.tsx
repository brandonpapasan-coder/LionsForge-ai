"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type {
  InvestigationProvenanceCategory,
  InvestigationProvenanceTimeline,
} from "@/lib/investigations";

const categories: Array<{ value: "all" | InvestigationProvenanceCategory; label: string }> = [
  { value: "all", label: "All activity" },
  { value: "claim", label: "Claims" },
  { value: "evidence", label: "Evidence" },
  { value: "validation", label: "Human judgments" },
  { value: "remediation_progress", label: "Current progress" },
  { value: "remediation_history", label: "Progress history" },
];

export function InvestigationProvenanceTimelinePanel({ investigationId }: { investigationId: number }) {
  const [timeline, setTimeline] = useState<InvestigationProvenanceTimeline | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [filter, setFilter] = useState<"all" | InvestigationProvenanceCategory>("all");
  const [reloadToken, setReloadToken] = useState(0);

  const reload = useCallback(() => {
    setTimeline(null);
    setUnavailable(false);
    setReloadToken((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch(`/api/investigations/${investigationId}/provenance-timeline`, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (response.status === 401) { window.location.href = "/login"; return; }
        if (!response.ok) throw new Error();
        const payload = (await response.json()) as InvestigationProvenanceTimeline;
        if (!controller.signal.aborted) setTimeline(payload);
      } catch {
        if (!controller.signal.aborted) setUnavailable(true);
      }
    }
    void load();
    return () => controller.abort();
  }, [investigationId, reloadToken]);

  const visibleEvents = useMemo(
    () => timeline?.events.filter((event) => filter === "all" || event.category === filter) ?? [],
    [filter, timeline],
  );

  return <section aria-label="Investigation provenance timeline">
    <h4>Investigation provenance timeline</h4>
    <p>This read-only history reports chronology and stored-record provenance. It is not validation evidence and does not establish truth, confidence, quality, completion, or resolution.</p>
    {timeline === null && !unavailable ? <p role="status">Loading investigation provenance…</p> : null}
    {unavailable ? <div role="status"><p>The investigation provenance timeline is temporarily unavailable.</p><button type="button" onClick={reload}>Retry provenance timeline</button></div> : null}
    {timeline?.status === "empty" ? <p>No stored claim, evidence, judgment, or remediation activity is available for this investigation.</p> : null}
    {timeline?.status === "active" ? <>
      <label>Activity category<select value={filter} onChange={(event) => setFilter(event.target.value as "all" | InvestigationProvenanceCategory)}>{categories.map((category) => <option key={category.value} value={category.value}>{category.label}</option>)}</select></label>
      {visibleEvents.length === 0 ? <p>No provenance events match this category.</p> : null}
      <ol>{visibleEvents.map((event) => <li key={event.event_key}>
        <article className="lesson-card" aria-label={`Provenance event ${event.event_key}`}>
          <div className="lesson-meta"><span>{event.category.replaceAll("_", " ")}</span><span>{event.authorship.replaceAll("_", " ")}</span></div>
          <p><strong>{event.action.replaceAll("_", " ")}</strong> — {event.summary}</p>
          {event.claim_statement ? <p><strong>Claim context:</strong> {event.claim_statement}</p> : null}
          <p><strong>Stored provenance:</strong> {event.source_table} record {event.source_record_id}</p>
          <time dateTime={event.occurred_at}>{new Date(event.occurred_at).toLocaleString()}</time>
        </article>
      </li>)}</ol>
    </> : null}
  </section>;
}
