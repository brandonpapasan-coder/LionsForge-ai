"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { AdaptiveLearningPlan as AdaptiveLearningPlanData } from "@/lib/education";

const isAbortError = (error: unknown) =>
  error instanceof DOMException && error.name === "AbortError";

export function AdaptiveLearningPlan() {
  const [plan, setPlan] = useState<AdaptiveLearningPlanData | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const mounted = useRef(false);

  const retry = useCallback(() => {
    setPlan(null);
    setUnavailable(false);
    setReloadToken((value) => value + 1);
  }, []);

  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();

    async function load() {
      try {
        const response = await fetch("/api/education/learning-plan", {
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
        const payload = (await response.json()) as AdaptiveLearningPlanData;
        if (!controller.signal.aborted && mounted.current) setPlan(payload);
      } catch (error) {
        if (!isAbortError(error) && mounted.current) setUnavailable(true);
      }
    }

    void load();
    return () => {
      mounted.current = false;
      controller.abort();
    };
  }, [reloadToken]);

  return (
    <section className="lesson-card" aria-label="Adaptive learning plan">
      <div className="lesson-meta">
        <span>evidence-backed next steps</span>
        <span>{plan?.items.length ?? 0} priorities</span>
      </div>
      <h2>Your adaptive learning plan</h2>
      <p>
        Measured performance and prerequisite rules shape this plan. Recommendations are advisory and remain yours to review.
      </p>

      {plan === null && !unavailable ? <p role="status">Building your learning plan from measured evidence…</p> : null}
      {unavailable ? (
        <div role="status">
          <p>Your learning plan is temporarily unavailable. Lessons and assessments remain available.</p>
          <button type="button" onClick={retry}>Retry learning plan</button>
        </div>
      ) : null}
      {plan?.status === "completed" ? (
        <p role="status">Your current curriculum is complete. New recommendations will appear when additional learning goals become available.</p>
      ) : null}
      {plan?.status === "active" && plan.items.length === 0 ? (
        <p>No learning-plan priorities are available yet.</p>
      ) : null}

      {plan?.items.map((item) => (
        <article key={item.lesson_slug} aria-label={`${item.title}: ${item.state}`} data-plan-state={item.state}>
          <div className="lesson-meta">
            <span>Step {item.sequence}</span>
            <span>{item.state.replaceAll("_", " ")}</span>
          </div>
          <h3>{item.title}</h3>
          <p>{item.reason}</p>
          <p>
            Target: {item.target_competency.replaceAll("-", " ")} · {item.recommended_difficulty} · mastery threshold {item.mastery_threshold}%
          </p>
          {item.state === "locked" && item.prerequisite_slugs.length > 0 ? (
            <p>Prerequisites: {item.prerequisite_slugs.map((slug) => slug.replaceAll("-", " ")).join(", ")}</p>
          ) : null}
          <details>
            <summary>Why this was recommended</summary>
            <ul>
              {item.signals.map((signal) => (
                <li key={`${signal.kind}:${signal.reference}`}>
                  <strong>{signal.kind.replaceAll("_", " ")}</strong>: {signal.explanation} ({signal.value})
                </li>
              ))}
            </ul>
          </details>
        </article>
      ))}
    </section>
  );
}
