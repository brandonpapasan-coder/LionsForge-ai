"use client";

import { useEffect, useRef, useState } from "react";

import type {
  AdaptiveAssessment,
  AssessmentAttempt,
  AssessmentResult,
  EducationHubData,
  Lesson,
} from "@/lib/education";

const isAbortError = (error: unknown) => error instanceof DOMException && error.name === "AbortError";

export function EducationHub() {
  const [data, setData] = useState<EducationHubData | null>(null);
  const [history, setHistory] = useState<AssessmentAttempt[] | null>(null);
  const [historyUnavailable, setHistoryUnavailable] = useState(false);
  const [assessment, setAssessment] = useState<AdaptiveAssessment | null>(null);
  const [assessmentResult, setAssessmentResult] = useState<AssessmentResult | null>(null);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);
  const [assessmentBusy, setAssessmentBusy] = useState(false);
  const mounted = useRef(false);
  const loadRequest = useRef<AbortController | null>(null);
  const lessonRequest = useRef<AbortController | null>(null);
  const assessmentRequest = useRef<AbortController | null>(null);
  const historyRequest = useRef<AbortController | null>(null);

  async function loadHistory() {
    historyRequest.current?.abort();
    const controller = new AbortController();
    historyRequest.current = controller;
    setHistoryUnavailable(false);
    try {
      const response = await fetch("/api/education/assessment/history", {
        cache: "no-store",
        signal: controller.signal,
      });
      if (controller.signal.aborted || !mounted.current || historyRequest.current !== controller) return;
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) {
        setHistoryUnavailable(true);
        return;
      }
      const attempts = (await response.json()) as AssessmentAttempt[];
      if (!controller.signal.aborted && mounted.current && historyRequest.current === controller) {
        setHistory(attempts);
      }
    } catch (requestError) {
      if (!isAbortError(requestError) && mounted.current && historyRequest.current === controller) {
        setHistoryUnavailable(true);
      }
    } finally {
      if (historyRequest.current === controller) historyRequest.current = null;
    }
  }

  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();
    loadRequest.current = controller;

    async function load() {
      try {
        const response = await fetch("/api/education", { cache: "no-store", signal: controller.signal });
        if (controller.signal.aborted || !mounted.current || loadRequest.current !== controller) return;
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) {
          setError("The Education Hub could not be loaded.");
          return;
        }
        const nextData = (await response.json()) as EducationHubData;
        if (!controller.signal.aborted && mounted.current && loadRequest.current === controller) setData(nextData);
      } catch (requestError) {
        if (!isAbortError(requestError) && mounted.current && loadRequest.current === controller) {
          setError("The education service is unavailable.");
        }
      } finally {
        if (loadRequest.current === controller) loadRequest.current = null;
      }
    }

    void load();
    void loadHistory();
    return () => {
      mounted.current = false;
      controller.abort();
      loadRequest.current = null;
      lessonRequest.current?.abort();
      lessonRequest.current = null;
      assessmentRequest.current?.abort();
      assessmentRequest.current = null;
      historyRequest.current?.abort();
      historyRequest.current = null;
    };
  }, []);

  async function startLesson(lesson: Lesson) {
    if (lesson.path_state === "locked" || lesson.status !== "not_started") return;
    lessonRequest.current?.abort();
    const controller = new AbortController();
    lessonRequest.current = controller;
    setUpdating(lesson.slug);
    setError(null);
    try {
      const response = await fetch(`/api/education/lessons/${lesson.slug}/progress`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ status: "in_progress", score: null }),
        signal: controller.signal,
      });
      if (controller.signal.aborted || !mounted.current || lessonRequest.current !== controller) return;
      if (!response.ok) {
        setError(response.status === 409 ? "Complete the prerequisite lessons before starting this lesson." : "Lesson progress could not be saved.");
        return;
      }
      const nextData = (await response.json()) as EducationHubData;
      if (!controller.signal.aborted && mounted.current && lessonRequest.current === controller) setData(nextData);
    } catch (requestError) {
      if (!isAbortError(requestError) && mounted.current && lessonRequest.current === controller) setError("The education service is unavailable.");
    } finally {
      if (lessonRequest.current === controller) {
        lessonRequest.current = null;
        if (mounted.current) setUpdating(null);
      }
    }
  }

  async function loadAssessment() {
    assessmentRequest.current?.abort();
    const controller = new AbortController();
    assessmentRequest.current = controller;
    setAssessmentBusy(true);
    setAssessmentResult(null);
    setSelectedOption(null);
    setError(null);
    try {
      const response = await fetch("/api/education/assessment", { cache: "no-store", signal: controller.signal });
      if (controller.signal.aborted || !mounted.current || assessmentRequest.current !== controller) return;
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) {
        setError(response.status === 409 ? "Complete-path learners do not have another assessment yet." : "The adaptive assessment could not be loaded.");
        return;
      }
      const nextAssessment = (await response.json()) as AdaptiveAssessment;
      if (!controller.signal.aborted && mounted.current && assessmentRequest.current === controller) setAssessment(nextAssessment);
    } catch (requestError) {
      if (!isAbortError(requestError) && mounted.current && assessmentRequest.current === controller) setError("The education service is unavailable.");
    } finally {
      if (assessmentRequest.current === controller) {
        assessmentRequest.current = null;
        if (mounted.current) setAssessmentBusy(false);
      }
    }
  }

  async function submitAssessment() {
    if (!assessment || selectedOption === null) return;
    assessmentRequest.current?.abort();
    const controller = new AbortController();
    assessmentRequest.current = controller;
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
        signal: controller.signal,
      });
      if (controller.signal.aborted || !mounted.current || assessmentRequest.current !== controller) return;
      if (!response.ok) {
        setError("The assessment response could not be scored.");
        return;
      }
      const result = (await response.json()) as AssessmentResult;
      if (!controller.signal.aborted && mounted.current && assessmentRequest.current === controller) {
        setAssessmentResult(result);
        setData(result.education_hub);
        setAssessment(null);
        setSelectedOption(null);
        void loadHistory();
      }
    } catch (requestError) {
      if (!isAbortError(requestError) && mounted.current && assessmentRequest.current === controller) setError("The education service is unavailable.");
    } finally {
      if (assessmentRequest.current === controller) {
        assessmentRequest.current = null;
        if (mounted.current) setAssessmentBusy(false);
      }
    }
  }

  if (error && !data) return <section className="education-state" role="alert">{error}</section>;
  if (!data) return <section className="education-state">Loading your learning path…</section>;

  const recommendedLesson = data.lessons.find((lesson) => lesson.slug === data.recommended_lesson_slug);
  const lessonTitle = (slug: string) => data.lessons.find((lesson) => lesson.slug === slug)?.title ?? slug.replaceAll("-", " ");

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
        <article><span>Curriculum progress</span><strong>{data.completion_percent}%</strong><p>{data.completed_lessons} of {data.total_lessons} lessons completed</p></article>
        <article><span>Assessment performance</span><strong>{data.average_score === null ? "—" : `${data.average_score}%`}</strong><p>{data.assessed_lessons} assessed lessons</p></article>
        <article><span>Recommended next step</span><strong>{recommendedLesson?.title ?? "Path complete"}</strong><p>{data.recommendation_reason}</p>{recommendedLesson ? <small>{recommendedLesson.estimated_minutes} minute {recommendedLesson.level} lesson</small> : null}</article>
      </section>

      <section className="lesson-card" aria-label="Adaptive competency assessment">
        <div className="lesson-meta"><span>adaptive assessment</span>{assessment ? <span>{assessment.difficulty}</span> : null}</div>
        <h2>Competency check</h2>
        {!assessment && !assessmentResult ? (
          <><p>Measure your current understanding and update your learning path with an explainable, competency-based checkpoint. Passing this check is the only way to complete a lesson.</p><button type="button" disabled={assessmentBusy || !data.recommended_lesson_slug} onClick={() => void loadAssessment()}>{assessmentBusy ? "Loading…" : data.recommended_lesson_slug ? "Begin assessment" : "Path complete"}</button></>
        ) : null}
        {assessment ? (
          <div><p><strong>{assessment.competency.replaceAll("-", " ")}</strong> · {assessment.difficulty_reason}</p><p>{assessment.question.objective}</p><fieldset><legend>{assessment.question.prompt}</legend>{assessment.question.options.map((option, index) => (<label key={option}><input type="radio" name="assessment-option" value={index} checked={selectedOption === index} onChange={() => setSelectedOption(index)} />{option}</label>))}</fieldset><button type="button" disabled={assessmentBusy || selectedOption === null} onClick={() => void submitAssessment()}>{assessmentBusy ? "Scoring…" : "Submit assessment"}</button></div>
        ) : null}
        {assessmentResult ? (
          <div role="status"><p><strong>{assessmentResult.score}% · {assessmentResult.passed ? "Passed" : "Needs review"}</strong></p><p>{assessmentResult.feedback}</p><p>Learning objective: {assessmentResult.learning_objective}</p><button type="button" disabled={assessmentBusy || !data.recommended_lesson_slug} onClick={() => void loadAssessment()}>{data.recommended_lesson_slug ? "Take next assessment" : "Learning path complete"}</button></div>
        ) : null}
      </section>

      <section className="lesson-card" aria-label="Mastery history">
        <div className="lesson-meta"><span>private learning evidence</span><span>{history?.length ?? 0} attempts</span></div>
        <h2>Mastery history</h2>
        {history === null && !historyUnavailable ? <p>Loading your assessment evidence…</p> : null}
        {historyUnavailable ? <p role="status">Mastery history is temporarily unavailable. Your lessons and assessments remain available.</p> : null}
        {history?.length === 0 ? <p>No assessment attempts yet. Your competency checks will appear here.</p> : null}
        {history && history.length > 0 ? (
          <div className="lesson-grid">
            {history.map((attempt) => (
              <article className="lesson-card" key={attempt.id} data-attempt-result={attempt.passed ? "passed" : "remediation"}>
                <div className="lesson-meta"><span>{attempt.difficulty}</span><span>{attempt.passed ? "mastery" : "remediation"}</span></div>
                <h3>{lessonTitle(attempt.lesson_slug)}</h3>
                <p>{attempt.competency.replaceAll("-", " ")}</p>
                <div className="lesson-footer"><strong>{attempt.score}% · {attempt.passed ? "Passed" : "Needs review"}</strong><time dateTime={attempt.created_at}>{new Date(attempt.created_at).toLocaleString()}</time></div>
              </article>
            ))}
          </div>
        ) : null}
      </section>

      <section className="competency-grid" aria-label="Competency mastery">
        {data.competencies.map((competency) => (<article key={competency.competency}><span>{competency.competency.replaceAll("-", " ")}</span><strong>{competency.mastery_percent}%</strong><p>{competency.proficiency_band} · {competency.average_score === null ? "not assessed" : `${competency.average_score}% average`}</p></article>))}
      </section>

      <section className="lesson-grid" aria-label="Adaptive learning path">
        {data.lessons.map((lesson) => {
          const locked = lesson.path_state === "locked";
          return (
            <article className="lesson-card" key={lesson.slug} data-path-state={lesson.path_state} data-recommended={lesson.slug === data.recommended_lesson_slug} aria-label={`${lesson.title}: ${lesson.path_state}`}>
              <div className="lesson-meta"><span>{lesson.level}</span><span>{lesson.estimated_minutes} min</span><span>{lesson.path_state}</span></div>
              <h2>{lesson.title}</h2><p>{lesson.description}</p><p>{lesson.path_reason}</p>
              {lesson.prerequisites.length > 0 ? <small>Prerequisites: {lesson.prerequisites.map((slug) => data.lessons.find((item) => item.slug === slug)?.title ?? slug).join(", ")}</small> : <small>No prerequisite lessons.</small>}
              <div className="lesson-footer"><span className={`lesson-status status-${lesson.status}`}>{lesson.status.replaceAll("_", " ")}</span>{lesson.status === "completed" ? <strong>Score {lesson.score ?? 100}%</strong> : locked ? <button type="button" disabled>Complete prerequisites</button> : lesson.status === "not_started" ? <button type="button" disabled={updating === lesson.slug} onClick={() => void startLesson(lesson)}>{updating === lesson.slug ? "Saving…" : "Start lesson"}</button> : <button type="button" disabled={assessmentBusy} onClick={() => void loadAssessment()}>{assessmentBusy ? "Loading…" : "Take competency check"}</button>}</div>
            </article>
          );
        })}
      </section>

      {error ? <p className="form-message" role="alert">{error}</p> : null}
    </div>
  );
}
