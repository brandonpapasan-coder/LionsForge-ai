"use client";

import { useEffect, useState } from "react";

import type { MarketLearningMastery } from "@/lib/market-learning-mastery";

const label = (value: string) => value.replaceAll("_", " ");

export function MarketLearningMasteryPanel() {
  const [assessment, setAssessment] = useState<MarketLearningMastery | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch("/api/market-simulator/learning-mastery", {
          cache: "no-store",
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) {
          setError("The market learning mastery assessment could not be loaded.");
          return;
        }
        setAssessment((await response.json()) as MarketLearningMastery);
      } catch (requestError) {
        if (!(requestError instanceof DOMException && requestError.name === "AbortError")) {
          setError("The market learning mastery service is unavailable.");
        }
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  if (error) return <section className="dashboard-state" role="alert">{error}</section>;
  if (!assessment) return <section className="dashboard-state" aria-live="polite">Loading mastery assessment…</section>;

  return (
    <section className="dashboard-panel" aria-labelledby="market-learning-mastery-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">EVIDENCE-BACKED MASTERY ASSESSMENT</p>
          <h2 id="market-learning-mastery-title">Measure educational reasoning discipline</h2>
          <p className="muted">{assessment.disclaimer}</p>
        </div>
        <div>
          <strong>{label(assessment.overall_readiness)}</strong>
          <p className="muted">{assessment.dimensions_met} of {assessment.dimensions_total} dimensions met</p>
        </div>
      </div>

      {assessment.overall_readiness === "not_started" ? (
        <div className="dashboard-state">
          <strong>Complete your first guided simulation.</strong>
          <p>A mastery profile appears after owner-scoped learning sessions and reflections are recorded.</p>
        </div>
      ) : (
        <div className="activity-list">
          {assessment.dimensions.map((dimension) => (
            <article className="activity-card" key={dimension.key}>
              <span>{dimension.evidence_count}/{dimension.target_count}</span>
              <div>
                <strong>{dimension.title}</strong>
                <p>{dimension.criteria}</p>
                <p><strong>Status:</strong> {label(dimension.status)}</p>
                {dimension.unmet_criteria.map((criterion) => <p className="muted" key={criterion}>{criterion}</p>)}
                <p><strong>Next action:</strong> {dimension.next_action}</p>
              </div>
            </article>
          ))}
        </div>
      )}

      <details>
        <summary>How the assessment is calculated</summary>
        <ul>{assessment.calculation_criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}</ul>
      </details>
    </section>
  );
}
