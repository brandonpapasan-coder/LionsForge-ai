"use client";

import { useState } from "react";

import type { ReviewQueueComparisonVerificationReceiptValidation } from "@/lib/investigations";

export function VerificationReceiptValidator() {
  const [file, setFile] = useState<File | null>(null);
  const [validating, setValidating] = useState(false);
  const [result, setResult] = useState<ReviewQueueComparisonVerificationReceiptValidation | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function validateReceipt() {
    if (!file) return;
    setValidating(true);
    setResult(null);
    setError(null);
    try {
      let parsed: unknown;
      try {
        parsed = JSON.parse(await file.text());
      } catch {
        setError("The selected receipt is not valid JSON.");
        return;
      }

      const response = await fetch(
        "/api/investigations/review-queue/snapshot/compare/report/verify/receipt/validate",
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(parsed),
          cache: "no-store",
        },
      );
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      const payload = await response.json();
      if (!response.ok) {
        const detail = typeof payload?.detail === "string"
          ? payload.detail
          : response.status === 422
            ? "The receipt contract or artifact type is unsupported."
            : "Verification receipt validation failed.";
        setError(detail);
        return;
      }
      setResult(payload as ReviewQueueComparisonVerificationReceiptValidation);
    } catch {
      setError("Verification receipt validation is temporarily unavailable. Retry validation.");
    } finally {
      setValidating(false);
    }
  }

  return (
    <section className="lesson-card" aria-label="Verification receipt validator">
      <div className="lesson-meta"><span>private artifact validation</span><span>integrity only</span></div>
      <h1>Validate a verification receipt</h1>
      <p>
        The selected receipt stays browser-local until explicit validation and is not stored by this
        interface. Validation checks the uploaded contract and canonical digest only; it does not read
        or compare current queue state.
      </p>
      <label>
        Verification receipt JSON
        <input
          aria-label="Verification receipt JSON"
          type="file"
          accept="application/json,.json"
          onChange={(event) => {
            setFile(event.target.files?.[0] ?? null);
            setResult(null);
            setError(null);
          }}
        />
      </label>
      <button type="button" disabled={!file || validating} onClick={() => void validateReceipt()}>
        {validating ? "Validating…" : "Validate verification receipt"}
      </button>
      {error ? <p role="alert">{error}</p> : null}
      {result ? (
        <div aria-label="Verification receipt validation results">
          <p><strong>Receipt integrity:</strong> valid</p>
          <p><strong>Receipt SHA-256:</strong> {result.recomputed_content_sha256}</p>
          <p><strong>Verified report SHA-256:</strong> {result.verified_report_content_sha256}</p>
          <p><strong>Prior snapshot SHA-256:</strong> {result.prior_content_sha256}</p>
          <p><strong>Current snapshot SHA-256:</strong> {result.current_content_sha256}</p>
          <p>
            <strong>Added:</strong> {result.added_item_count} · <strong>Removed:</strong>{" "}
            {result.removed_item_count} · <strong>Unchanged:</strong> {result.unchanged_item_count}
          </p>
          <p>
            <strong>Investigation count delta:</strong>{" "}
            {result.investigation_count_delta > 0 ? "+" : ""}{result.investigation_count_delta}
          </p>
          <h2>Preserved reason-count deltas</h2>
          {Object.keys(result.reason_count_deltas).length === 0 ? (
            <p>No preserved reason-count changes.</p>
          ) : (
            <ul>
              {Object.entries(result.reason_count_deltas).map(([reason, delta]) => (
                <li key={reason}>
                  {reason.replaceAll("_", " ")}: {delta > 0 ? "+" : ""}{delta}
                </li>
              ))}
            </ul>
          )}
          <p><strong>Verification contract:</strong> {result.verification_contract_version}</p>
          <p><strong>Current queue checked:</strong> no</p>
          <p>{result.interpretation_notice}</p>
        </div>
      ) : null}
    </section>
  );
}
