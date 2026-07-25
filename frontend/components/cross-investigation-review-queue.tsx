"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type {
  CrossInvestigationReviewQueue,
  ReviewQueueReason,
  ReviewQueueSnapshotComparison,
} from "@/lib/investigations";

const reasonOptions: Array<{ value: "all" | ReviewQueueReason; label: string }> = [
  { value: "all", label: "All review reasons" },
  { value: "stale_validation", label: "Stale validation" },
  { value: "missing_validation", label: "Missing validation" },
  { value: "unresolved_contradiction", label: "Unresolved contradiction" },
  { value: "blocked_remediation", label: "Blocked remediation" },
  { value: "remediation_ready_for_review", label: "Ready for review" },
];

function downloadFilename(contentDisposition: string | null, fallback: string) {
  const match = contentDisposition?.match(/filename="?([^";]+)"?/i);
  return match?.[1] ?? fallback;
}

export function CrossInvestigationReviewQueuePanel() {
  const [queue, setQueue] = useState<CrossInvestigationReviewQueue | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [comparisonFile, setComparisonFile] = useState<File | null>(null);
  const [comparisonPayload, setComparisonPayload] = useState<unknown>(null);
  const [comparing, setComparing] = useState(false);
  const [comparison, setComparison] = useState<ReviewQueueSnapshotComparison | null>(null);
  const [comparisonError, setComparisonError] = useState<string | null>(null);
  const [reportExporting, setReportExporting] = useState(false);
  const [reportExportError, setReportExportError] = useState<string | null>(null);
  const [reportDigest, setReportDigest] = useState<string | null>(null);
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
        const response = await fetch("/api/investigations/review-queue", { cache: "no-store", signal: controller.signal });
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

  async function downloadSnapshot() {
    setExporting(true);
    setExportError(null);
    try {
      const response = await fetch("/api/investigations/review-queue/snapshot", { cache: "no-store" });
      if (response.status === 401) { window.location.href = "/login"; return; }
      if (!response.ok) throw new Error();
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = downloadFilename(response.headers.get("content-disposition"), "lionsforge-review-queue-snapshot.json");
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch {
      setExportError("The review queue snapshot could not be exported. No file was downloaded.");
    } finally {
      setExporting(false);
    }
  }

  async function compareSnapshot() {
    if (!comparisonFile) return;
    setComparing(true);
    setComparison(null);
    setComparisonPayload(null);
    setComparisonError(null);
    setReportExportError(null);
    setReportDigest(null);
    try {
      let parsed: unknown;
      try { parsed = JSON.parse(await comparisonFile.text()); }
      catch { setComparisonError("The selected file is not valid JSON."); return; }
      const response = await fetch("/api/investigations/review-queue/snapshot/compare", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(parsed),
        cache: "no-store",
      });
      if (response.status === 401) { window.location.href = "/login"; return; }
      const payload = await response.json();
      if (!response.ok) {
        const detail = typeof payload?.detail === "string" ? payload.detail : "Snapshot comparison failed.";
        setComparisonError(detail);
        return;
      }
      setComparisonPayload(parsed);
      setComparison(payload as ReviewQueueSnapshotComparison);
    } catch {
      setComparisonError("The snapshot comparison is temporarily unavailable.");
    } finally {
      setComparing(false);
    }
  }

  async function downloadComparisonReport() {
    if (!comparison || !comparisonPayload) return;
    setReportExporting(true);
    setReportExportError(null);
    setReportDigest(null);
    try {
      const response = await fetch("/api/investigations/review-queue/snapshot/compare/report", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(comparisonPayload),
        cache: "no-store",
      });
      if (response.status === 401) { window.location.href = "/login"; return; }
      if (!response.ok) {
        let detail = "The comparison report could not be exported. No file was downloaded.";
        try {
          const payload = await response.json();
          if (typeof payload?.detail === "string") detail = `${payload.detail} No file was downloaded.`;
        } catch { /* preserve deterministic fallback */ }
        setReportExportError(detail);
        return;
      }
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = downloadFilename(
        response.headers.get("content-disposition"),
        "lionsforge-review-queue-comparison-report.json",
      );
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setReportDigest(response.headers.get("x-content-sha256"));
    } catch {
      setReportExportError("The comparison report could not be exported. No file was downloaded.");
    } finally {
      setReportExporting(false);
    }
  }

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
    {queue !== null ? <>
      <button type="button" disabled={exporting} onClick={() => void downloadSnapshot()}>{exporting ? "Preparing snapshot…" : "Download queue snapshot"}</button>
      <p>The snapshot digest verifies export integrity only. It is not validation evidence or advice and does not establish truth, confidence, importance, urgency, risk, resolution, or recommended action.</p>
      {exportError ? <p role="alert">{exportError}</p> : null}
      <div className="lesson-card">
        <h3>Compare a prior snapshot</h3>
        <p>The selected JSON remains private to explicit comparison and report-export requests and is not stored by this interface.</p>
        <label>Prior snapshot JSON<input aria-label="Prior snapshot JSON" type="file" accept="application/json,.json" onChange={(event) => { setComparisonFile(event.target.files?.[0] ?? null); setComparison(null); setComparisonPayload(null); setComparisonError(null); setReportExportError(null); setReportDigest(null); }} /></label>
        <button type="button" disabled={!comparisonFile || comparing} onClick={() => void compareSnapshot()}>{comparing ? "Comparing…" : "Compare snapshot"}</button>
        {comparisonError ? <p role="alert">{comparisonError}</p> : null}
        {comparison ? <div aria-label="Snapshot comparison results">
          <p><strong>Added:</strong> {comparison.added_items.length} · <strong>Removed:</strong> {comparison.removed_items.length} · <strong>Unchanged:</strong> {comparison.unchanged_items.length}</p>
          <p><strong>Investigation count delta:</strong> {comparison.investigation_count_delta > 0 ? "+" : ""}{comparison.investigation_count_delta}</p>
          <h4>Reason-count deltas</h4>
          {Object.keys(comparison.reason_count_deltas).length === 0 ? <p>No reason-count changes.</p> : <ul>{Object.entries(comparison.reason_count_deltas).map(([reason, delta]) => <li key={reason}>{reason.replaceAll("_", " ")}: {delta > 0 ? "+" : ""}{delta}</li>)}</ul>}
          <p>{comparison.interpretation_notice}</p>
          <button type="button" disabled={reportExporting} onClick={() => void downloadComparisonReport()}>{reportExporting ? "Preparing report…" : "Download comparison report"}</button>
          <p>The report digest verifies exported artifact integrity only. The report describes stored workflow-state changes and is not validation evidence, advice, or a truth, confidence, importance, urgency, risk, resolution, or recommended-action judgment.</p>
          {reportDigest ? <p aria-label="Comparison report digest"><strong>Report SHA-256:</strong> {reportDigest}</p> : null}
          {reportExportError ? <p role="alert">{reportExportError}</p> : null}
        </div> : null}
      </div>
    </> : null}
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
