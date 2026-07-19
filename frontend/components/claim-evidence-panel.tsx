"use client";

import { FormEvent, useEffect, useState } from "react";
import type {
  AssessmentLevel,
  ClaimEvidence,
  ClaimValidationSummary,
  EvidenceRelationship,
  EvidenceType,
  InvestigationClaim,
  InvestigationValidationSummary,
} from "@/lib/investigations";

const evidenceTypes: EvidenceType[] = ["primary", "secondary", "dataset", "expert", "other"];
const relationships: EvidenceRelationship[] = ["supports", "contradicts", "neutral"];
const assessmentLevels: AssessmentLevel[] = ["low", "medium", "high"];

export function ClaimEvidencePanel({ investigationId }: { investigationId: number }) {
  const [claims, setClaims] = useState<InvestigationClaim[] | null>(null);
  const [evidence, setEvidence] = useState<Record<number, ClaimEvidence[]>>({});
  const [claimSummaries, setClaimSummaries] = useState<Record<number, ClaimValidationSummary>>({});
  const [investigationSummary, setInvestigationSummary] = useState<InvestigationValidationSummary | null>(null);
  const [statement, setStatement] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function loadClaims() {
      try {
        const response = await fetch(`/api/investigations/${investigationId}/claims`, { cache: "no-store" });
        if (!response?.ok) throw new Error();
        const payload: unknown = await response.json();
        if (!Array.isArray(payload)) throw new Error();
        if (active) setClaims(payload as InvestigationClaim[]);
      } catch {
        if (active) {
          setClaims([]);
          setError("Claims and evidence are temporarily unavailable.");
        }
      }
    }
    void loadClaims();
    return () => { active = false; };
  }, [investigationId]);

  async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
    const response = await fetch(url, { ...init, cache: "no-store" });
    if (!response.ok) throw new Error();
    return (await response.json()) as T;
  }

  async function createClaim(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await requestJson<InvestigationClaim>(`/api/investigations/${investigationId}/claims`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ statement }),
      });
      setClaims((current) => [created, ...(current ?? [])]);
      setStatement("");
    } catch {
      setError("The claim could not be created.");
    } finally {
      setBusy(false);
    }
  }

  async function loadEvidence(claimId: number) {
    setError(null);
    try {
      const items = await requestJson<ClaimEvidence[]>(`/api/investigations/claims/${claimId}/evidence`);
      setEvidence((current) => ({ ...current, [claimId]: items }));
    } catch {
      setError("Evidence could not be loaded.");
    }
  }

  async function loadClaimSummary(claimId: number) {
    try {
      const summary = await requestJson<ClaimValidationSummary>(`/api/investigations/claims/${claimId}/summary`);
      setClaimSummaries((current) => ({ ...current, [claimId]: summary }));
    } catch {
      setError("The claim validation summary could not be loaded.");
    }
  }

  async function loadInvestigationSummary() {
    try {
      setInvestigationSummary(await requestJson<InvestigationValidationSummary>(`/api/investigations/${investigationId}/validation-summary`));
    } catch {
      setError("The investigation validation summary could not be loaded.");
    }
  }

  async function createEvidence(claimId: number, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      const created = await requestJson<ClaimEvidence>(`/api/investigations/claims/${claimId}/evidence`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          source_title: String(data.get("source_title") ?? "").trim(),
          source_url: String(data.get("source_url") ?? "").trim(),
          evidence_type: String(data.get("evidence_type") ?? "primary"),
          relationship: String(data.get("relationship") ?? "supports"),
          notes: String(data.get("notes") ?? "").trim() || null,
        }),
      });
      setEvidence((current) => ({ ...current, [claimId]: [created, ...(current[claimId] ?? [])] }));
      form.reset();
    } catch {
      setError("The evidence reference could not be attached. Check the source URL and required fields.");
    } finally {
      setBusy(false);
    }
  }

  async function assessClaim(claimId: number, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const updated = await requestJson<InvestigationClaim>(`/api/investigations/claims/${claimId}/assessment`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          confidence_level: String(data.get("confidence_level") || "") || null,
          confidence_rationale: String(data.get("confidence_rationale") || "").trim() || null,
        }),
      });
      setClaims((current) => current?.map((claim) => claim.id === claimId ? updated : claim) ?? []);
      await loadClaimSummary(claimId);
    } catch {
      setError("Claim confidence requires a valid level and written rationale.");
    } finally {
      setBusy(false);
    }
  }

  async function assessEvidence(claimId: number, evidenceId: number, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const updated = await requestJson<ClaimEvidence>(`/api/investigations/evidence/${evidenceId}/assessment`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          credibility_rating: String(data.get("credibility_rating") || "") || null,
          credibility_rationale: String(data.get("credibility_rationale") || "").trim() || null,
        }),
      });
      setEvidence((current) => ({
        ...current,
        [claimId]: (current[claimId] ?? []).map((item) => item.id === evidenceId ? updated : item),
      }));
      await loadClaimSummary(claimId);
    } catch {
      setError("Evidence credibility requires a valid rating and written rationale.");
    } finally {
      setBusy(false);
    }
  }

  async function deleteClaim(claimId: number) {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/investigations/claims/${claimId}`, { method: "DELETE" });
      if (!response.ok) throw new Error();
      setClaims((current) => current?.filter((claim) => claim.id !== claimId) ?? []);
      setEvidence((current) => { const next = { ...current }; delete next[claimId]; return next; });
    } catch {
      setError("The claim could not be deleted.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Claims and evidence">
      <h4>Claims and evidence</h4>
      <p>Assessments are user-entered judgments, not automated declarations of truth.</p>
      <button type="button" disabled={busy} onClick={() => void loadInvestigationSummary()}>Show validation summary</button>
      {investigationSummary ? (
        <div aria-label="Investigation validation summary">
          <p>{investigationSummary.assessed_claim_count} of {investigationSummary.claim_count} claims assessed.</p>
          <p>Confidence: {investigationSummary.low_confidence_count} low · {investigationSummary.medium_confidence_count} medium · {investigationSummary.high_confidence_count} high</p>
          <p>{investigationSummary.unresolved_contradiction_count} claims contain unresolved contradictory evidence.</p>
        </div>
      ) : null}
      <form onSubmit={createClaim}>
        <label>Claim statement<textarea value={statement} required maxLength={4000} onChange={(event) => setStatement(event.target.value)} /></label>
        <button type="submit" disabled={busy}>Add claim</button>
      </form>
      {claims === null && !error ? <p>Loading claims…</p> : null}
      {claims?.length === 0 && !error ? <p>No claims mapped yet.</p> : null}
      {claims?.map((claim) => {
        const summary = claimSummaries[claim.id];
        return (
          <article key={claim.id} className="lesson-card">
            <h5>{claim.statement}</h5>
            <p>Confidence: {claim.confidence_level ?? "not assessed"}</p>
            {claim.confidence_rationale ? <p>{claim.confidence_rationale}</p> : null}
            <div>
              <button type="button" disabled={busy} onClick={() => void loadEvidence(claim.id)}>Show evidence</button>
              <button type="button" disabled={busy} onClick={() => void loadClaimSummary(claim.id)}>Show claim summary</button>
              <button type="button" disabled={busy} onClick={() => void deleteClaim(claim.id)}>Delete claim</button>
            </div>
            {summary ? (
              <div aria-label={`Validation summary for ${claim.statement}`}>
                <p>{summary.supporting_count} supporting · {summary.contradicting_count} contradicting · {summary.neutral_count} neutral</p>
                <p>{summary.assessed_evidence_count} of {summary.total_evidence_count} evidence sources assessed.</p>
                {summary.has_unresolved_contradiction ? <p>Unresolved contradiction requires review.</p> : null}
              </div>
            ) : null}
            <form aria-label={`Assess confidence for ${claim.statement}`} onSubmit={(event) => void assessClaim(claim.id, event)}>
              <label>Confidence level<select name="confidence_level" defaultValue={claim.confidence_level ?? ""}><option value="">Not assessed</option>{assessmentLevels.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
              <label>Confidence rationale<textarea name="confidence_rationale" defaultValue={claim.confidence_rationale ?? ""} maxLength={4000} /></label>
              <button type="submit" disabled={busy}>Save claim assessment</button>
            </form>
            <form aria-label={`Attach evidence to ${claim.statement}`} onSubmit={(event) => void createEvidence(claim.id, event)}>
              <label>Source title<input name="source_title" required maxLength={300} /></label>
              <label>Source URL<input name="source_url" type="url" required /></label>
              <label>Evidence type<select name="evidence_type" defaultValue="primary">{evidenceTypes.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
              <label>Relationship<select name="relationship" defaultValue="supports">{relationships.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
              <label>Notes<textarea name="notes" maxLength={4000} /></label>
              <button type="submit" disabled={busy}>Attach evidence</button>
            </form>
            {(evidence[claim.id] ?? []).map((item) => (
              <div key={item.id} data-evidence-relationship={item.relationship}>
                <a href={item.source_url} target="_blank" rel="noreferrer"><strong>{item.source_title}</strong></a>
                <p>{item.evidence_type} · {item.relationship}</p>
                {item.notes ? <p>{item.notes}</p> : null}
                <p>Credibility: {item.credibility_rating ?? "not assessed"}</p>
                {item.credibility_rationale ? <p>{item.credibility_rationale}</p> : null}
                <form aria-label={`Assess credibility for ${item.source_title}`} onSubmit={(event) => void assessEvidence(claim.id, item.id, event)}>
                  <label>Credibility rating<select name="credibility_rating" defaultValue={item.credibility_rating ?? ""}><option value="">Not assessed</option>{assessmentLevels.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
                  <label>Credibility rationale<textarea name="credibility_rationale" defaultValue={item.credibility_rationale ?? ""} maxLength={4000} /></label>
                  <button type="submit" disabled={busy}>Save evidence assessment</button>
                </form>
              </div>
            ))}
          </article>
        );
      })}
      {error ? <p role="alert">{error}</p> : null}
    </section>
  );
}
