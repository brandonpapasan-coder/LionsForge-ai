"use client";

import { useCallback, useEffect, useState } from "react";

import type { ClaimEvidenceValidationMap } from "@/lib/investigations";

export function ClaimEvidenceValidationMapPanel({ investigationId }: { investigationId: number }) {
  const [validationMap, setValidationMap] = useState<ClaimEvidenceValidationMap | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const retry = useCallback(() => {
    setValidationMap(null);
    setUnavailable(false);
    setReloadToken((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch(`/api/investigations/${investigationId}/validation-map`, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) {
          setUnavailable(true);
          return;
        }
        const payload = (await response.json()) as ClaimEvidenceValidationMap;
        if (!controller.signal.aborted) setValidationMap(payload);
      } catch {
        if (!controller.signal.aborted) setUnavailable(true);
      }
    }
    void load();
    return () => controller.abort();
  }, [investigationId, reloadToken]);

  return (
    <section aria-label="Claim evidence validation map">
      <h4>Claim-evidence validation map</h4>
      <p>Deterministic rules organize recorded evidence. These statuses do not establish objective truth and remain subject to human review.</p>
      {validationMap === null && !unavailable ? <p role="status">Mapping claims to recorded evidence…</p> : null}
      {unavailable ? (
        <div role="status">
          <p>The validation map is temporarily unavailable.</p>
          <button type="button" onClick={retry}>Retry validation map</button>
        </div>
      ) : null}
      {validationMap?.status === "empty" ? <p>No material claims are recorded for this investigation.</p> : null}
      {validationMap?.claims.map((claim) => (
        <article key={claim.claim_id} className="lesson-card" aria-label={`${claim.statement}: ${claim.status}`}>
          <div className="lesson-meta"><span>Claim {claim.sequence}</span><span>{claim.status}</span></div>
          <h5>{claim.statement}</h5>
          <p>{claim.status_rule}</p>
          <p>Human review: {claim.human_review.status.replaceAll("_", " ")}</p>
          {claim.human_review.rationale ? <p>Reviewer rationale: {claim.human_review.rationale}</p> : null}
          {claim.evidence_links.length > 0 ? (
            <ul aria-label={`Evidence for ${claim.statement}`}>
              {claim.evidence_links.map((evidence) => (
                <li key={evidence.evidence_id}>
                  <a href={evidence.source_url} target="_blank" rel="noreferrer">{evidence.source_title}</a>
                  {` · ${evidence.relationship} · ${evidence.evidence_type}`}
                  <p>{evidence.classification_rule}</p>
                  {evidence.credibility_rating ? <p>Credibility input: {evidence.credibility_rating}</p> : null}
                </li>
              ))}
            </ul>
          ) : <p>No evidence links are recorded.</p>}
          {claim.missing_evidence_requirements.length > 0 ? (
            <div><strong>Missing evidence</strong><ul>{claim.missing_evidence_requirements.map((item) => <li key={item}>{item}</li>)}</ul></div>
          ) : null}
          {claim.unresolved_gaps.length > 0 ? (
            <div><strong>Unresolved gaps</strong><ul>{claim.unresolved_gaps.map((item) => <li key={item}>{item}</li>)}</ul></div>
          ) : null}
        </article>
      ))}
    </section>
  );
}
