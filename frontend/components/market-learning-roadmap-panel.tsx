"use client";

import { useEffect, useState } from "react";

import type { MarketLearningRoadmap } from "@/lib/market-learning-roadmap";

const label = (value: string) => value.replaceAll("_", " ");

export function MarketLearningRoadmapPanel() {
  const [roadmap, setRoadmap] = useState<MarketLearningRoadmap | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch("/api/market-simulator/learning-roadmap", {
          cache: "no-store",
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) {
          setError("The adaptive learning roadmap could not be loaded.");
          return;
        }
        setRoadmap((await response.json()) as MarketLearningRoadmap);
      } catch (requestError) {
        if (!(requestError instanceof DOMException && requestError.name === "AbortError")) {
          setError("The adaptive learning roadmap service is unavailable.");
        }
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  if (error) return <section className="dashboard-state" role="alert">{error}</section>;
  if (!roadmap) return <section className="dashboard-state" aria-live="polite">Loading adaptive learning roadmap…</section>;

  return (
    <section className="dashboard-panel" aria-labelledby="learning-roadmap-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">ADAPTIVE LEARNING ROADMAP</p>
          <h2 id="learning-roadmap-title">Turn portfolio gaps into next actions</h2>
          <p className="muted">{roadmap.disclaimer}</p>
        </div>
        <strong>{label(roadmap.status)}</strong>
      </div>

      {roadmap.tasks.length === 0 ? (
        <div className="dashboard-state">
          <strong>{roadmap.status === "not_started" ? "Begin your first guided simulation." : "Current roadmap complete."}</strong>
          <p>{roadmap.status === "not_started" ? "Complete a scenario and record a reflection to create your first task queue." : "Repeat scenarios with new assumptions and continue evidence review to deepen learning."}</p>
        </div>
      ) : (
        <div className="activity-list">
          {roadmap.tasks.map((task, index) => (
            <article className="activity-card" key={task.task_key}>
              <span>{index + 1}</span>
              <div>
                <strong>{task.title}</strong>
                <p>{task.rationale}</p>
                <p><strong>Complete when:</strong> {task.completion_criteria}</p>
                <p><strong>Reflection:</strong> {task.reflection_prompt}</p>
                <p className="muted">Priority {task.priority} · {label(task.task_type)}</p>
              </div>
            </article>
          ))}
        </div>
      )}

      <details>
        <summary>How priorities are calculated</summary>
        <ul>{roadmap.calculation_criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}</ul>
      </details>
    </section>
  );
}
