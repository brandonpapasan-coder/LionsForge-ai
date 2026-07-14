"use client";

import { useEffect, useState } from "react";

import type {
  AdaptiveAssessment,
  AssessmentResult,
  EducationHubData,
  Lesson,
} from "@/lib/education";

export function EducationHub() {
  const [data, setData] = useState<EducationHubData | null>(null);
  const [assessment, setAssessment] = useState<AdaptiveAssessment | null>(null);
  const [assessmentResult, setAssessmentResult] = useState<AssessmentResult | null>(null);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);
  const [assessmentBusy, setAssessmentBusy] = useState(false);

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

  async function loadAssessment() {
    setAssessmentBusy(true);
    setAssessmentResult(null);
    setSelectedOption(null);
    setError(null);
    try {
      const response = await fetch("/api/education/assessment", { cache: "no-store" });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) {
        setError(response.status === 409 ? "Complete-path learners do not have another assessment yet." : "The adaptive assessment could not be loaded.");
        return;
      }
      setAssessment((await response.json()) as AdaptiveAssessment);
    } catch {
      setError("The education service is unavailable.");
    } finally {
      setAssessmentBusy(false);
    }
  }

  async function submitAssessment() {
    if (!assessment || selectedOption === null) return;
    setAssessmentBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/education/assessment", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          question_id: assessment.question.id,
          selected_option: selectedOption,
        }),
      });
      if (!response.ok) {
        setError("The assessment response could not be scored.");
        return;
      }
      const result = (await response.json()) as AssessmentResult;
      setAssessmentResult(result);
      setData(result.education_hub);
      setAssessment(null);
      setSelectedOption(null);
    } catch {
      setError("The education service is unavailable.");
    } finally {
      setAssessmentBusy(false);
    }
  }

  if (error && !data) return <section className="education-state" role="alert">{error}</section>;
  if (!data) return <section className="education-state">Loading your learning path…</section>;

  const recommendedLesson = data.lessons.find((lesson) => lesson.slug === data.recommended_lesson_slug);

  return (
    <div className="education-shell">
      <header className="education-hero">
        <div>
          <p className="eyebrow">EDUCATION HUB</p>
          <h1>Build durable mastery.</h1>
          <p>Complete focused lessons and adaptive competency checks that strengthen research quality and decision-making.</p>
        </div>
        <div className="education-progress-ring" aria-label={`${data.mastery_percent}% mastery`}>
          <strong>{data.mastery_percent}%</strong>
          <span>{data.proficiency_band} mastery</span>
        </div>
      </header>

      <section className="competency-grid" aria-label="Learning overview">
        <article>
          <span>Curriculum progress</span>
          <strong>{data.completion_percent}%</strong>
          <p>{data.completed_lessons} of {data.total_lessons} lessons completed</p>
        </article>
        <article>
          <span>Assessment performance</span>
          <strong>{data.average_score === null ? "—" : `${data.average_score}%`}</strong>
          <p>{data.assessed_lessons} assessed lessons</p>
        </article>
        <article>
          <span>Recommended next step</span>
          <strong>{recommendedLesson?.title ?? "Path complete"}</strong>
          <p>{data.recommendation_reason}</p>
          {recommendedLesson ? <small>{recommendedLesson.estimated_minutes} minute {recommendedLesson.level} lesson</small> : null}
        </article>
      </section>

      <section className="lesson-card" aria-label="Adaptive competency assessment">
        <div className="lesson-meta">
          <span>adaptive assessment</span>
          {assessment ? <span>{assessment.difficulty}</span> : null}
        </div>
        <h2>Competency check</h2>
        {!assessment && !assessmentResult ? (
          <>
            <p>Measure your current understanding and update your learning path with an explainable, competency-based checkpoint.</p>
            <button type="button" disabled={assessmentBusy || !data.recommended_lesson_slug} onClick={() => void loadAssessment()}>
              {assessmentBusy ? "Loading…" : data.recommended_lesson_slug ? "Begin assessment" : "Path complete"}
            </button>
          </>
        ) : null}
        {assessment ? (
          <div>
            <p><strong>{assessment.competency.replaceAll("-", " ")}</strong> · {assessment.difficulty_reason}</p>
            <p>{assessment.question.objective}</p>
            <fieldset>
              <legend>{assessment.question.prompt}</legend>
              {assessment.question.options.map((option, index) => (
                <label key={option}>
                  <input
                    type="radio"
                    name="assessment-option"
                    value={index}
                    checked={selectedOption === index}
                    onChange={() => setSelectedOption(index)}
                  />
                  {option}
                </label>
              ))}
            </fieldset>
            <button type="button" disabled={assessmentBusy || selectedOption === null} onClick={() => void submitAssessment()}>
              {assessmentBusy ? "Scoring…" : "Submit assessment"}
            </button>
          </div>
        ) : null}
        {assessmentResult ? (
          <div role="status">
            <p><strong>{assessmentResult.score}% · {assessmentResult.passed ? "Passed" : "Needs review"}</strong></p>
            <p>{assessmentResult.feedback}</p>
            <p>Learning objective: {assessmentResult.learning_objective}</p>
            <button type="button" disabled={assessmentBusy || !data.recommended_lesson_slug} onClick={() => void loadAssessment()}>
              {data.recommended_lesson_slug ? "Take next assessment" : "Learning path complete"}
            </button>
          </div>
        ) : null}
      </section>

      <section className="competency-grid" aria-label="Competency mastery">
        {data.competencies.map((competency) => (
          <article key={competency.competency}>
            <span>{competency.competency.replaceAll("-", " ")}</span>
            <strong>{competency.mastery_percent}%</strong>
            <p>{competency.proficiency_band} · {competency.average_score === null ? "not assessed" : `${competency.average_score}% average`}</p>
          </article>
        ))}
      </section>

      <section className="lesson-grid">
        {data.lessons.map((lesson) => (
          <article className="lesson-card" key={lesson.slug} data-recommended={lesson.slug === data.recommended_lesson_slug}>
            <div className="lesson-meta">
              <span>{lesson.level}</span>
              <span>{lesson.estimated_minutes} min</span>
              {lesson.slug === data.recommended_lesson_slug ? <span>recommended</span> : null}
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
