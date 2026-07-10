"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import type { AssessmentResult } from "@/lib/education";

type LessonAssessmentProps = {
  courseId: string;
  moduleId: string;
  question: string;
  options: string[];
  completed: boolean;
};

export function LessonAssessment({ courseId, moduleId, question, options, completed }: LessonAssessmentProps) {
  const router = useRouter();
  const [result, setResult] = useState<AssessmentResult | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    const form = new FormData(event.currentTarget);
    const selectedOption = Number(form.get("answer"));

    try {
      const response = await fetch(`/api/education/courses/${courseId}/modules/${moduleId}/assessment`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ selected_option: selectedOption }),
      });
      const payload = (await response.json()) as AssessmentResult;
      setResult(payload);
      if (payload.passed) router.refresh();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="lesson-assessment" onSubmit={handleSubmit}>
      <h2>Knowledge check</h2>
      <p>{question}</p>
      <div className="assessment-options">
        {options.map((option, index) => (
          <label key={option}>
            <input type="radio" name="answer" value={index} required />
            <span>{option}</span>
          </label>
        ))}
      </div>
      <button type="submit" disabled={submitting || completed}>
        {completed ? "Assessment passed" : submitting ? "Scoring..." : "Submit assessment"}
      </button>
      {result ? (
        <div className={`assessment-result ${result.passed ? "passed" : "failed"}`} role="status">
          <strong>{result.score}% · {result.passed ? "Passed" : "Review required"}</strong>
          <p>{result.explanation}</p>
        </div>
      ) : null}
    </form>
  );
}
