"use client";

import { useEffect, useState } from "react";

import type { ResearchTrustIndex } from "@/lib/research-trust-index";

const isAbortError = (error: unknown) => error instanceof DOMException && error.name === "AbortError";
const score = (value: number) => `${Math.round(value)}%`;
const label = (value: string) => value.replaceAll("_", " ");

type ResearchTrustPanelProps = {
  projectId: number;
};

export function ResearchTrustPanel({ projectId }: ResearchTrustPanelProps) {
  const [data, setData] = useState<ResearchTrustIndex | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setError(null);
    setLoading(true);

    async function load() {
      try {
        const response = await fetch(`/api/research-trust-index/projects/${projectId}`, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (response.status === 404) {
          setError("Research trust data is not available for this project.");
          return;
        }
        if (!response.ok) {
          setError("Research trust data could not be loaded.");
          return;
        }
        setData((await response.json()) as ResearchTrustIndex);
      } catch (requestError) {
        if (!isAbortError(requestError) && !controller.signal.aborted) {
          setError("The research trust service is unavailable.");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void load();
    return () => controller.abort();
  }, [projectId]);

  if (loading) {
    return <section className="dashboard-state" aria-live="polite">Loading project trust index…</section>;
  }

  if (error) {
    return <section className="dashboard-state" role="alert">{error}</section>;
  }

  if (!data) return null;

  const validationStability = data.components.find((component) => component.key === "validation_stability");

  return (
    <section className="dashboard-panel" aria-labelledby="research-trust-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">RESEARCH TRUST INDEX</p>
          <h3 id="research-trust-title">Project evidence confidence</h3>
          <p className="muted">Methodology {data.methodology_version} · Confidence {label(data.confidence_level)}</p>
        </div>
      </div>

      <div className="metric-grid" aria-label="Research trust metrics">
        <article className="metric-card"><span>Overall trust</span><strong>{score(data.overall_score)}</strong><p>{data.evidence_count} evidence records assessed</p></article>
        <article className="metric-card"><span>Validation stability</span><strong>{validationStability ? score(validationStability.score) : "Not scored"}</strong><p>{data.review_event_count} review events across {data.reviewed_evidence_count} evidence records</p></article>
        <article className="metric-card"><span>Review reversals</span><strong>{data.review_reversal_count}</strong><p>Status changes after initial review</p></article>
        <article className="metric-card"><span>Open conflicts</span><strong>{data.conflict_count}</strong><p>{data.contradicting_count} contradicting evidence records</p></article>
      </div>

      <div className="dashboard-grid">
        <section>
          <div className="panel-heading"><div><p className="eyebrow">TRUST COMPONENTS</p><h3>How confidence is formed</h3></div></div>
          <div className="activity-list">
            {data.components.map((component) => (
              <div className="activity-card" key={component.key}>
                <span>{score(component.score)}</span>
                <div><strong>{component.label}</strong><p>{component.explanation}</p></div>
              </div>
            ))}
          </div>
        </section>

        <section>
          <div className="panel-heading"><div><p className="eyebrow">PRIORITY ACTIONS</p><h3>What improves trust next</h3></div></div>
          <div className="activity-list">
            {data.recommended_actions.length ? data.recommended_actions.map((action) => (
              <div className="activity-card" key={action}><span>Action</span><div><strong>{action}</strong></div></div>
            )) : <p className="muted">No additional trust actions are currently recommended.</p>}
          </div>
        </section>
      </div>
    </section>
  );
}
