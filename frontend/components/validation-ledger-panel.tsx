"use client";

import { FormEvent, useEffect, useState } from "react";

import type {
  AssessmentLevel,
  ClaimValidationJudgment,
  InvestigationClaim,
  ValidationStatus,
} from "@/lib/investigations";

const statuses: ValidationStatus[] = ["unreviewed", "supported", "mixed", "contradicted", "insufficient"];
const confidenceLevels: AssessmentLevel[] = ["low", "medium", "high"];

export function ValidationLedgerPanel({ investigationId }: { investigationId: number }) {
  const [claims, setClaims] = useState<InvestigationClaim[]>([]);
  const [judgments, setJudgments] = useState<Record<number, ClaimValidationJudgment[]>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadClaims() {
      try {
        const response = await fetch(`/api/investigations/${investigationId}/claims`, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!response.ok) throw new Error();
        const payload = (await response.json()) as InvestigationClaim[];
        setClaims(payload);
      } catch {
        if (!controller.signal.aborted) {
          setError("Validation history is temporarily unavailable.");
        }
      }
    }

    void loadClaims();
    return () => controller.abort();
  }, [investigationId]);

  async function loadHistory(claimId: number) {
    setError(null);
    try {
      const response = await fetch(`/api/investigations/claims/${claimId}/judgments`, { cache: "no-store" });
      if (!response.ok) throw new Error();
      const history = (await response.json()) as ClaimValidationJudgment[];
      setJudgments((current) => ({ ...current, [claimId]: history }));
    } catch {
      setError("Validation history could not be loaded.");
    }
  }

  async function recordJudgment(claimId: number, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      const response = await fetch(`/api/investigations/claims/${claimId}/judgments`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          validation_status: String(data.get("validation_status")),
          confidence_level: String(data.get("confidence_level")),
          rationale: String(data.get("rationale") ?? "").trim(),
          unresolved_questions: String(data.get("unresolved_questions") ?? "").trim() || null,
        }),
      });
      if (!response.ok) throw new Error();
      const created = (await response.json()) as ClaimValidationJudgment;
      setJudgments((current) => ({ ...current, [claimId]: [created, ...(current[claimId] ?? [])] }));
      form.reset();
    } catch {
      setError("A validation judgment requires a status, confidence level, and written rationale.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Append-only validation ledger">
      <h4>Validation ledger</h4>
      <p>Each review is preserved as an immutable historical judgment. Stale records require a new review rather than editing the old one.</p>
      {claims.map((claim) => (
        <article key={claim.id} className="lesson-card">
          <h5>{claim.statement}</h5>
          <button type="button" disabled={busy} onClick={() => void loadHistory(claim.id)}>Show validation history</button>
          <form aria-label={`Record validation judgment for ${claim.statement}`} onSubmit={(event) => void recordJudgment(claim.id, event)}>
            <label>Validation status<select name="validation_status" defaultValue="insufficient">{statuses.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
            <label>Confidence level<select name="confidence_level" defaultValue="medium">{confidenceLevels.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
            <label>Review rationale<textarea name="rationale" required maxLength={4000} /></label>
            <label>Unresolved questions<textarea name="unresolved_questions" maxLength={4000} /></label>
            <button type="submit" disabled={busy}>Record immutable judgment</button>
          </form>
          {(judgments[claim.id] ?? []).map((judgment) => (
            <div key={judgment.id} data-validation-stale={judgment.is_stale}>
              <p><strong>{judgment.validation_status}</strong> · {judgment.confidence_level} confidence</p>
              <p>{judgment.rationale}</p>
              {judgment.unresolved_questions ? <p>Unresolved: {judgment.unresolved_questions}</p> : null}
              <p>Reviewed {new Date(judgment.reviewed_at).toLocaleString()}</p>
              {judgment.is_stale ? <p role="status">Stale judgment: the claim or evidence changed after this review.</p> : null}
            </div>
          ))}
        </article>
      ))}
      {error ? <p role="alert">{error}</p> : null}
    </section>
  );
}
