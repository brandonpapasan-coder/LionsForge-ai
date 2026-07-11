"use client";

import { useEffect, useState } from "react";

import type { EducationHubData, Lesson } from "@/lib/education";

export function EducationHub() {
  const [data, setData] = useState<EducationHubData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const response = await fetch("/api/education", { cache: "no-store" });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) {
        setError("The Education Hub could not be loaded.");
        return;
      }
      setData((await response.json()) as EducationHubData);
    }
    void load();
  }, []);

  async function updateLesson(lesson: Lesson, status: "in_progress" | "completed") {
    setUpdating(lesson.slug);
    setError(null);
    try {
      const response = await fetch(`/api/education/lessons/${lesson.slug}/progress`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ status, score: status === "completed" ? 100 : null }),
      });
      if (!response.ok) {
        setError("Lesson progress could not be saved.");
        return;
      }
      setData((await response.json()) as EducationHubData);
    } catch {
      setError("The education service is unavailable.");
    } finally {
      setUpdating(null);
    }
  }

  if (error && !data) return <section className="education-state" role="alert">{error}</section>;
  if (!data) return <section className="education-state">Loading your learning path…</section>;

  return (
    <div className="education-shell">
      <header className="education-hero">
        <div>
          <p className="eyebrow">EDUCATION HUB</p>
          <h1>Build durable mastery.</h1>
          <p>Complete focused lessons that directly strengthen research quality and decision-making.</p>
        </div>
        <div className="education-progress-ring" aria-label={`${data.completion_percent}% complete`}>
          <strong>{data.completion_percent}%</strong>
          <span>{data.completed_lessons} of {data.total_lessons} lessons</span>
        </div>
      </header>

      <section className="competency-grid">
        {data.competencies.map((competency) => (
          <article key={competency.competency}>
            <span>{competency.competency.replaceAll("-", " ")}</span>
            <strong>{competency.mastery_percent}%</strong>
            <p>{competency.completed_lessons} of {competency.total_lessons} completed</p>
          </article>
        ))}
      </section>

      <section className="lesson-grid">
        {data.lessons.map((lesson) => (
          <article className="lesson-card" key={lesson.slug}>
            <div className="lesson-meta">
              <span>{lesson.level}</span>
              <span>{lesson.estimated_minutes} min</span>
            </div>
            <h2>{lesson.title}</h2>
            <p>{lesson.description}</p>
            <div className="lesson-footer">
              <span className={`lesson-status status-${lesson.status}`}>{lesson.status.replaceAll("_", " ")}</span>
              {lesson.status === "completed" ? (
                <strong>Score {lesson.score ?? 100}%</strong>
              ) : (
                <button
                  type="button"
                  disabled={updating === lesson.slug}
                  onClick={() => void updateLesson(lesson, lesson.status === "not_started" ? "in_progress" : "completed")}
                >
                  {updating === lesson.slug ? "Saving…" : lesson.status === "not_started" ? "Start lesson" : "Complete lesson"}
                </button>
              )}
            </div>
          </article>
        ))}
      </section>

      {error ? <p className="form-message" role="alert">{error}</p> : null}
    </div>
  );
}
