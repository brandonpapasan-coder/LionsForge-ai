"use client";

import { useEffect, useState } from "react";

import type { ResearchEvidenceProvenanceLedger } from "@/lib/research-evidence-provenance";

const label = (value: string) => value.replaceAll("_", " ");
const isAbortError = (error: unknown) => error instanceof DOMException && error.name === "AbortError";
const formatScore = (value: number) => `${Math.round(value * 100)}%`;

export function ResearchProvenancePanel({ projectId }: { projectId: number }) {
  const [ledger, setLedger] = useState<ResearchEvidenceProvenanceLedger | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    setLedger(null);

    async function load() {
      try {
        const response = await fetch(`/api/research-evidence-provenance/ledger?project_id=${projectId}`, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) {
          setError("Provenance history could not be loaded for this project.");
          return;
        }
        setLedger((await response.json()) as ResearchEvidenceProvenanceLedger);
      } catch (requestError) {
        if (!isAbortError(requestError) && !controller.signal.aborted) {
          setError("The provenance service is unavailable.");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void load();
    return () => controller.abort();
  }, [projectId]);

  if (loading) {
    return <section className="dashboard-state" aria-live="polite">Loading evidence provenance…</section>;
  }

  if (error) {
    return <section className="dashboard-state" role="alert">{error}</section>;
  }

  if (!ledger || ledger.entries.length === 0) {
    return (
      <section className="dashboard-panel" aria-labelledby="provenance-title">
        <div className="panel-heading"><div><p className="eyebrow">EVIDENCE PROVENANCE</p><h3 id="provenance-title">Trace claim history</h3></div></div>
        <div className="dashboard-state">
          <strong>No provenance entries yet.</strong>
          <p>Add evidence or review an existing claim to begin an auditable project timeline.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="dashboard-panel" aria-labelledby="provenance-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">EVIDENCE PROVENANCE</p>
          <h3 id="provenance-title">Trace claim history</h3>
          <p className="muted">{ledger.disclaimer}</p>
        </div>
      </div>

      <div className="research-card-grid">
        <article><span>Evidence</span><strong>{ledger.summary.total_evidence}</strong><p>Recorded claims in this project.</p></article>
        <article><span>Events</span><strong>{ledger.summary.total_events}</strong><p>Creation, review, and supersession events.</p></article>
        <article><span>Contradictions</span><strong>{ledger.summary.unresolved_contradictions}</strong><p>Unresolved contradiction groups.</p></article>
        <article><span>Source warnings</span><strong>{ledger.summary.missing_source_metadata}</strong><p>Entries missing expected source metadata.</p></article>
      </div>

      <div className="activity-list">
        {ledger.entries.map((entry) => (
          <article className="activity-card" key={entry.event_id}>
            <span>{label(entry.event_type)}</span>
            <div>
              <strong>{entry.source_title}</strong>
              <p>{entry.claim}</p>
              <p><strong>Status:</strong> {label(entry.validation_status)} · <strong>Source:</strong> {label(entry.source_type)}</p>
              {entry.source_url ? <p><strong>URL:</strong> <a href={entry.source_url} target="_blank" rel="noreferrer">Open source</a></p> : null}
              {entry.author || entry.publisher ? <p><strong>Attribution:</strong> {[entry.author, entry.publisher].filter(Boolean).join(" · ")}</p> : null}
              {entry.published_at ? <p><strong>Published:</strong> {new Date(entry.published_at).toLocaleString()}</p> : null}
              <p><strong>Quality:</strong> credibility {formatScore(entry.credibility_score)} · freshness {formatScore(entry.freshness_score)} · confidence {formatScore(entry.confidence_score)}</p>
              <p className="muted"><strong>Fingerprint:</strong> <code>{entry.fingerprint}</code></p>
              {entry.reviewer_notes ? <p><strong>Review notes:</strong> {entry.reviewer_notes}</p> : null}
              {entry.contradiction_key ? <p><strong>Contradiction key:</strong> {entry.contradiction_key}</p> : null}
              {entry.supersedes_evidence_id ? <p><strong>Supersedes evidence:</strong> #{entry.supersedes_evidence_id}</p> : null}
              {entry.warning ? <p role="alert"><strong>Warning:</strong> {entry.warning}</p> : null}
              <p className="muted">{new Date(entry.occurred_at).toLocaleString()}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
