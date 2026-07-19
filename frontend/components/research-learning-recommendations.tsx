"use client";

import { useState } from "react";

import type { InvestigationEducationRecommendations } from "@/lib/investigations";

export function ResearchLearningRecommendations({ investigationId }: { investigationId: number }) {
  const [data, setData] = useState<InvestigationEducationRecommendations | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadRecommendations() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/investigations/${investigationId}/education-recommendations`, {
        cache: "no-store",
      });
      if (!response.ok) throw new Error();
      setData((await response.json()) as InvestigationEducationRecommendations);
    } catch {
      setError("Learning recommendations are temporarily unavailable. Your investigation and Education Hub remain available.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section aria-label="Research learning recommendations">
      <h4>Learning recommendations</h4>
      <p>Recommendations explain research-skill gaps. Only adaptive assessments can complete lessons.</p>
      <button type="button" disabled={loading} onClick={() => void loadRecommendations()}>
        {loading ? "Analyzing gaps…" : "Analyze learning gaps"}
      </button>
      {data ? (
        <div>
          <p>{data.recommendation_count} recommendation{data.recommendation_count === 1 ? "" : "s"}</p>
          <p>Completion authority: adaptive assessment only.</p>
          {data.recommendations.length === 0 ? <p>No research-learning gaps were identified.</p> : null}
          {data.recommendations.map((item) => (
            <article className="lesson-card" key={`${item.lesson_slug}-${item.gap_type}`} data-gap-type={item.gap_type}>
              <div className="lesson-meta"><span>{item.competency.replaceAll("-", " ")}</span><span>priority {item.priority}</span></div>
              <h5>{item.lesson_title}</h5>
              <p>{item.reason}</p>
              <a href={`/education#${item.lesson_slug}`}>Open lesson in Education Hub</a>
            </article>
          ))}
        </div>
      ) : null}
      {error ? <p role="alert">{error}</p> : null}
    </section>
  );
}
