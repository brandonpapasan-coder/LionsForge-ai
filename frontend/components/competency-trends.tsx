"use client";

import { useEffect, useRef, useState } from "react";

import type { CompetencyTrend } from "@/lib/education";

const isAbortError = (error: unknown) => error instanceof DOMException && error.name === "AbortError";

export function CompetencyTrends() {
  const [trends, setTrends] = useState<CompetencyTrend[] | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();

    async function load() {
      try {
        const response = await fetch("/api/education/assessment/trends", {
          cache: "no-store",
          signal: controller.signal,
        });
        if (controller.signal.aborted || !mounted.current) return;
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) {
          setUnavailable(true);
          return;
        }
        const payload = (await response.json()) as CompetencyTrend[];
        if (!controller.signal.aborted && mounted.current) setTrends(payload);
      } catch (error) {
        if (!isAbortError(error) && mounted.current) setUnavailable(true);
      }
    }

    void load();
    return () => {
      mounted.current = false;
      controller.abort();
    };
  }, []);

  return (
    <section className="lesson-card" aria-label="Competency trends">
      <div className="lesson-meta"><span>explainable learning momentum</span><span>{trends?.length ?? 0} competencies</span></div>
      <h2>Competency trends</h2>
      {trends === null && !unavailable ? <p>Analyzing your recent assessment evidence…</p> : null}
      {unavailable ? <p role="status">Competency trends are temporarily unavailable. Your lessons and assessments remain available.</p> : null}
      {trends?.length === 0 ? <p>No assessment evidence is available yet.</p> : null}
      {trends && trends.length > 0 ? (
        <div className="competency-grid">
          {trends.map((trend) => (
            <article key={trend.competency} data-trend-direction={trend.direction}>
              <span>{trend.competency.replaceAll("-", " ")}</span>
              <strong>{trend.direction.replaceAll("_", " ")}</strong>
              <p>{trend.explanation}</p>
              <small>
                {trend.attempt_count} attempts · recent {trend.recent_average === null ? "—" : `${trend.recent_average}%`} · prior {trend.prior_average === null ? "—" : `${trend.prior_average}%`}
              </small>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}
