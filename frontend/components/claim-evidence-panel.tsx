"use client";

import { FormEvent, useEffect, useState } from "react";
import type { ClaimEvidence, InvestigationClaim } from "@/lib/investigations";

export function ClaimEvidencePanel({ investigationId }: { investigationId: number }) {
  const [claims, setClaims] = useState<InvestigationClaim[] | null>(null);
  const [evidence, setEvidence] = useState<Record<number, ClaimEvidence[]>>({});
  const [statement, setStatement] = useState("");
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
    setError(null);
    const response = await fetch(`/api/investigations/${investigationId}/claims`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ statement }),
    });
    if (!response.ok) {
      setError("The claim could not be created.");
      return;
    }
    const created = (await response.json()) as InvestigationClaim;
    setClaims((current) => [created, ...(current ?? [])]);
    setStatement("");
  }

  async function loadEvidence(claimId: number) {
    const response = await fetch(`/api/investigations/claims/${claimId}/evidence`, { cache: "no-store" });
    if (!response.ok) {
      setError("Evidence could not be loaded.");
      return;
    }
    setEvidence((current) => ({ ...current, [claimId]: (await response.json()) as ClaimEvidence[] }));
  }

  return (
    <section aria-label="Claims and evidence">
      <h4>Claims and evidence</h4>
      <form onSubmit={createClaim}>
        <label>Claim statement<textarea value={statement} required maxLength={4000} onChange={(event) => setStatement(event.target.value)} /></label>
        <button type="submit">Add claim</button>
      </form>
      {claims === null && !error ? <p>Loading claims…</p> : null}
      {claims?.length === 0 ? <p>No claims mapped yet.</p> : null}
      {claims?.map((claim) => (
        <article key={claim.id} className="lesson-card">
          <h5>{claim.statement}</h5>
          <button type="button" onClick={() => void loadEvidence(claim.id)}>Show evidence</button>
          {(evidence[claim.id] ?? []).map((item) => (
            <div key={item.id} data-evidence-relationship={item.relationship}>
              <strong>{item.source_title}</strong>
              <p>{item.evidence_type} · {item.relationship}</p>
            </div>
          ))}
        </article>
      ))}
      {error ? <p role="alert">{error}</p> : null}
    </section>
  );
}
