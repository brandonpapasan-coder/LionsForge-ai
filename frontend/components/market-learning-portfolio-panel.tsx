"use client";

import { useEffect, useState } from "react";

import type { MarketLearningPortfolio } from "@/lib/market-learning-portfolio";

const isAbortError = (error: unknown) => error instanceof DOMException && error.name === "AbortError";
const label = (value: string) => value.replaceAll("_", " ");

export function MarketLearningPortfolioPanel() {
  const [data, setData] = useState<MarketLearningPortfolio | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        const response = await fetch("/api/market-simulator/learning-portfolio", {
          cache: "no-store",
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) {
          setError("The market learning portfolio could not be loaded.");
          return;
        }
        setData((await response.json()) as MarketLearningPortfolio);
      } catch (requestError) {
        if (!isAbortError(requestError) && !controller.signal.aborted) {
          setError("The market learning portfolio service is unavailable.");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void load();
    return () => controller.abort();
  }, []);

  if (loading) {
    return <section className="dashboard-state" aria-live="polite">Loading market learning portfolio…</section>;
  }
  if (error) {
    return <section className="dashboard-state" role="alert">{error}</section>;
  }
  if (!data) return null;

  return (
    <section className="dashboard-panel" aria-labelledby="market-learning-portfolio-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">EVIDENCE-BACKED LEARNING PORTFOLIO</p>
          <h2 id="market-learning-portfolio-title">Auditable market learning</h2>
          <p className="muted">{data.disclaimer}</p>
        </div>
      </div>

      {data.completed_sessions === 0 ? (
        <div className="dashboard-state">
          <strong>No market learning portfolio yet.</strong>
          <p>Complete a guided simulation and reflection to begin an auditable educational record.</p>
        </div>
      ) : (
        <>
          <div className="metric-grid" aria-label="Market learning portfolio metrics">
            <article className="metric-card"><span>Learning maturity</span><strong>{label(data.learning_maturity)}</strong><p>Based on transparent completion and review criteria</p></article>
            <article className="metric-card"><span>Scenario breadth</span><strong>{data.unique_scenarios}</strong><p>{data.completed_sessions} completed educational simulations</p></article>
            <article className="metric-card"><span>Submitted claims</span><strong>{data.submitted_evidence}</strong><p>Simulated educational evidence only</p></article>
            <article className="metric-card"><span>Review history</span><strong>{data.immutable_review_events}</strong><p>Immutable evidence-review events</p></article>
          </div>

          <div className="dashboard-grid">
            <section>
              <div className="panel-heading"><div><p className="eyebrow">MATURITY CRITERIA</p><h3>How this level was calculated</h3></div></div>
              <div className="activity-list">
                {data.maturity_criteria.map((criterion) => (
                  <div className="activity-card" key={criterion}><span>✓</span><div><strong>{criterion}</strong></div></div>
                ))}
              </div>
            </section>

            <section>
              <div className="panel-heading"><div><p className="eyebrow">VALIDATION DISTRIBUTION</p><h3>Learning-claim review status</h3></div></div>
              <div className="activity-list">
                {Object.keys(data.validation_status_counts).length === 0 ? (
                  <p className="muted">Submit a completed learning session as evidence to begin the review cycle.</p>
                ) : Object.entries(data.validation_status_counts).map(([status, count]) => (
                  <div className="activity-card" key={status}><span>{count}</span><div><strong>{label(status)}</strong><p>Simulated learning claims</p></div></div>
                ))}
              </div>
            </section>
          </div>

          <section>
            <div className="panel-heading"><div><p className="eyebrow">RECENT REVIEWED CLAIMS</p><h3>Continue the learning cycle</h3></div></div>
            <div className="activity-list">
              {data.recent_claims.length === 0 ? <p className="muted">No submitted learning claims yet.</p> : data.recent_claims.map((claim) => (
                <article className="activity-card" key={claim.evidence_id}>
                  <span>{label(claim.validation_status)}</span>
                  <div>
                    <strong>{label(claim.scenario_name)} · {label(claim.risk_tier)} risk</strong>
                    <p>{claim.claim}</p>
                    <p><strong>Reviewer notes:</strong> {claim.reviewer_notes ?? "No reviewer notes yet."}</p>
                    <p><strong>Next reflection:</strong> {claim.next_reflection_prompt}</p>
                    <p>{claim.review_event_count} immutable review event{claim.review_event_count === 1 ? "" : "s"}</p>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </>
      )}
    </section>
  );
}
