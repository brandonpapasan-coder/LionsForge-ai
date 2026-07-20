"use client";

import { useEffect, useState } from "react";

import type {
  InvestigationQualityAssessment,
  QualityAssessmentDimension,
  QualityAssessmentStatus,
} from "@/lib/investigations";

const statusLabels: Record<QualityAssessmentStatus, string> = {
  missing: "Missing",
  partial: "Partial",
  complete: "Complete",
};

function countSummary(dimension: QualityAssessmentDimension) {
  const entries = Object.entries(dimension.counts);
  if (entries.length === 0) return null;
  return entries
    .map(([key, value]) => `${key.replaceAll("_", " ")}: ${value}`)
    .join(" · ");
}

export function InvestigationQualityAssessmentPanel({ investigationId }: { investigationId: number }) {
  const [assessment, setAssessment] = useState<InvestigationQualityAssessment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/investigations/${investigationId}/quality-assessment`, {
        cache: "no-store",
      });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) throw new Error();
      setAssessment((await response.json()) as InvestigationQualityAssessment);
    } catch {
      setError("The investigation quality checklist is temporarily unavailable.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [investigationId]);

  return (
    <section className="lesson-card" aria-label="Investigation quality assessment">
      <div className="lesson-meta">
        <span>research completeness</span>
        {assessment ? <span>contract {assessment.contract_version}</span> : null}
      </div>
      <h4>Investigation quality checklist</h4>
      <p>
        Review concrete gaps before treating a synthesis as decision-ready. This checklist describes stored research state and does not score truth.
      </p>
      <button type="button" disabled={loading} onClick={() => void load()}>
        {loading ? "Checking…" : "Refresh checklist"}
      </button>
      {assessment ? (
        <div aria-live="polite">
          <div className="lesson-grid">
            {assessment.dimensions.map((dimension) => (
              <article
                className="lesson-card"
                key={dimension.key}
                data-quality-status={dimension.status}
              >
                <div className="lesson-meta">
                  <span>{statusLabels[dimension.status]}</span>
                  <span>{dimension.key.replaceAll("_", " ")}</span>
                </div>
                <h5>{dimension.label}</h5>
                <p>{dimension.explanation}</p>
                {countSummary(dimension) ? <p>{countSummary(dimension)}</p> : null}
              </article>
            ))}
          </div>
          <section aria-label="Recommended research actions">
            <h5>Recommended next actions</h5>
            {assessment.recommendations.length === 0 ? (
              <p>No checklist gaps are currently identified. Human review is still required before relying on the synthesis.</p>
            ) : (
              <ol>
                {assessment.recommendations.map((recommendation) => (
                  <li key={recommendation}>{recommendation}</li>
                ))}
              </ol>
            )}
          </section>
          <p>{assessment.interpretation_notice}</p>
          <p>
            Generated from stored state {new Date(assessment.generated_from_stored_state_at).toLocaleString()}.
          </p>
        </div>
      ) : !loading && !error ? <p>No assessment is available.</p> : null}
      {error ? <p role="alert">{error}</p> : null}
    </section>
  );
}
