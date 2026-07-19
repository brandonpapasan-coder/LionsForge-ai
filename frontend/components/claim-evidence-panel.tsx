"use client";

import { FormEvent, useEffect, useState } from "react";
import type { ClaimEvidence, EvidenceRelationship, EvidenceType, InvestigationClaim } from "@/lib/investigations";

const evidenceTypes: EvidenceType[] = ["primary", "secondary", "dataset", "expert", "other"];
const relationships: EvidenceRelationship[] = ["supports", "contradicts", "neutral"];

export function ClaimEvidencePanel({ investigationId }: { investigationId: number }) {
  const [claims, setClaims] = useState<InvestigationClaim[] | null>(null);
  const [evidence, setEvidence] = useState<Record<number, ClaimEvidence[]>>({});
  const [statement, setStatement] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch(`/api/investigations/${investigationId}/claims`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error();
        const items = (await response.json()) as InvestigationClaim[];
        if (active) setClaims(items);
      })
      .catch(() => active && setError("Claims and evidence are temporarily unavailable."));
    return () => { active = false; };
  }, [investigationId]);

  async function createClaim(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/investigations/${investigationId}/claims`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ statement }),
      });
      if (!response.ok) throw new Error();
      const created = (await response.json()) as InvestigationClaim;
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
    const response = await fetch(`/api/investigations/claims/${claimId}/evidence`, { cache: "no-store" });
    if (!response.ok) {
      setError("Evidence could not be loaded.");
      return;
    }
    const items = (await response.json()) as ClaimEvidence[];
    setEvidence((current) => ({ ...current, [claimId]: items }));
  }

  async function createEvidence(claimId: number, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      const response = await fetch(`/api/investigations/claims/${claimId}/evidence`, {
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
      if (!response.ok) throw new Error();
      const created = (await response.json()) as ClaimEvidence;
      setEvidence((current) => ({ ...current, [claimId]: [created, ...(current[claimId] ?? [])] }));
      form.reset();
    } catch {
      setError("The evidence reference could not be attached. Check the source URL and required fields.");
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
      setEvidence((current) => {
        const next = { ...current };
        delete next[claimId];
        return next;
      });
    } catch {
      setError("The claim could not be deleted.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Claims and evidence">
      <h4>Claims and evidence</h4>
      <form onSubmit={createClaim}>
        <label>Claim statement<textarea value={statement} required maxLength={4000} onChange={(event) => setStatement(event.target.value)} /></label>
        <button type="submit" disabled={busy}>Add claim</button>
      </form>
      {claims === null && !error ? <p>Loading claims…</p> : null}
      {claims?.length === 0 ? <p>No claims mapped yet.</p> : null}
      {claims?.map((claim) => (
        <article key={claim.id} className="lesson-card">
          <h5>{claim.statement}</h5>
          <div>
            <button type="button" disabled={busy} onClick={() => void loadEvidence(claim.id)}>Show evidence</button>
            <button type="button" disabled={busy} onClick={() => void deleteClaim(claim.id)}>Delete claim</button>
          </div>
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
            </div>
          ))}
        </article>
      ))}
      {error ? <p role="alert">{error}</p> : null}
    </section>
  );
}
