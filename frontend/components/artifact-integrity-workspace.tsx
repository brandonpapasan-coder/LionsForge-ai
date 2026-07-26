"use client";

import { useState } from "react";

import type {
  ReviewQueueArtifactIntegrityResult,
  ReviewQueueComparisonReportVerification,
  ReviewQueueComparisonVerificationReceiptValidation,
} from "@/lib/investigations";

function deltas(values: Record<string, number>) {
  const entries = Object.entries(values);
  if (entries.length === 0) return <p>No preserved reason-count changes.</p>;
  return <ul>{entries.map(([reason, delta]) => <li key={reason}>{reason.replaceAll("_", " ")}: {delta > 0 ? "+" : ""}{delta}</li>)}</ul>;
}

export function ArtifactIntegrityWorkspace() {
  const [file, setFile] = useState<File | null>(null);
  const [validating, setValidating] = useState(false);
  const [result, setResult] = useState<ReviewQueueArtifactIntegrityResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function validateArtifact() {
    if (!file) return;
    setValidating(true);
    setResult(null);
    setError(null);
    try {
      let parsed: unknown;
      try {
        parsed = JSON.parse(await file.text());
      } catch {
        setError("The selected artifact is not valid JSON.");
        return;
      }
      const response = await fetch("/api/investigations/review-queue/artifacts/validate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(parsed),
        cache: "no-store",
      });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      const payload = await response.json();
      if (!response.ok) {
        const detail = typeof payload?.detail === "string"
          ? payload.detail
          : response.status === 422
            ? "The artifact type, version, or contract is unsupported."
            : "Artifact integrity validation failed.";
        setError(detail);
        return;
      }
      setResult(payload as ReviewQueueArtifactIntegrityResult);
    } catch {
      setError("Artifact integrity validation is temporarily unavailable. Retry validation.");
    } finally {
      setValidating(false);
    }
  }

  const reportValidation = result?.detected_artifact_type === "cross_investigation_review_queue_comparison_report"
    ? result.validation as ReviewQueueComparisonReportVerification
    : null;
  const receiptValidation = result?.detected_artifact_type === "cross_investigation_review_queue_comparison_verification_receipt"
    ? result.validation as ReviewQueueComparisonVerificationReceiptValidation
    : null;

  return <section className="lesson-card" aria-label="Artifact integrity workspace">
    <div className="lesson-meta"><span>private artifact validation</span><span>integrity only</span></div>
    <h1>Artifact integrity workspace</h1>
    <p>Upload a supported comparison report or verification receipt. The file stays browser-local until explicit validation and is not stored by this interface. Validation checks contract and canonical digest only and does not read current queue state.</p>
    <label>Review-queue artifact JSON<input aria-label="Review-queue artifact JSON" type="file" accept="application/json,.json" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setResult(null); setError(null); }} /></label>
    <button type="button" disabled={!file || validating} onClick={() => void validateArtifact()}>{validating ? "Validating…" : "Validate artifact"}</button>
    {error ? <p role="alert">{error}</p> : null}
    {result ? <div aria-label="Artifact integrity results">
      <p><strong>Artifact integrity:</strong> valid</p>
      <p><strong>Detected artifact:</strong> {result.detected_artifact_type === "cross_investigation_review_queue_comparison_report" ? "comparison report" : "verification receipt"}</p>
      {reportValidation ? <>
        <p><strong>Report SHA-256:</strong> {reportValidation.recomputed_content_sha256}</p>
        <p><strong>Prior snapshot SHA-256:</strong> {reportValidation.prior_content_sha256}</p>
        <p><strong>Current snapshot SHA-256:</strong> {reportValidation.current_content_sha256}</p>
        <p><strong>Added:</strong> {reportValidation.added_item_count} · <strong>Removed:</strong> {reportValidation.removed_item_count} · <strong>Unchanged:</strong> {reportValidation.unchanged_item_count}</p>
        <p><strong>Investigation count delta:</strong> {reportValidation.investigation_count_delta > 0 ? "+" : ""}{reportValidation.investigation_count_delta}</p>
        <h2>Preserved reason-count deltas</h2>
        {deltas(reportValidation.reason_count_deltas)}
      </> : null}
      {receiptValidation ? <>
        <p><strong>Receipt SHA-256:</strong> {receiptValidation.recomputed_content_sha256}</p>
        <p><strong>Verified report SHA-256:</strong> {receiptValidation.verified_report_content_sha256}</p>
        <p><strong>Prior snapshot SHA-256:</strong> {receiptValidation.prior_content_sha256}</p>
        <p><strong>Current snapshot SHA-256:</strong> {receiptValidation.current_content_sha256}</p>
        <p><strong>Added:</strong> {receiptValidation.added_item_count} · <strong>Removed:</strong> {receiptValidation.removed_item_count} · <strong>Unchanged:</strong> {receiptValidation.unchanged_item_count}</p>
        <p><strong>Investigation count delta:</strong> {receiptValidation.investigation_count_delta > 0 ? "+" : ""}{receiptValidation.investigation_count_delta}</p>
        <h2>Preserved reason-count deltas</h2>
        {deltas(receiptValidation.reason_count_deltas)}
      </> : null}
      <p><strong>Current queue checked:</strong> no</p>
      <p>{result.interpretation_notice}</p>
    </div> : null}
  </section>;
}
