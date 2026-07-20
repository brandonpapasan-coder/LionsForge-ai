import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EducationHub } from "@/components/education-hub";
import type {
  AdaptiveAssessment,
  AssessmentAttempt,
  AssessmentResult,
  EducationHubData,
  Lesson,
} from "@/lib/education";

const lessons: Lesson[] = [
  {
    slug: "financial-statements-foundations",
    title: "Financial Statements Foundations",
    description: "Read financial statements as one connected system.",
    level: "foundation",
    competency: "financial-statements",
    estimated_minutes: 35,
    prerequisites: [],
    status: "completed",
    score: 90,
    completed_at: "2026-07-14T19:00:00Z",
    path_state: "completed",
    path_reason: "Lesson completed and prerequisite credit earned.",
  },
  {
    slug: "valuation-and-cash-flow",
    title: "Valuation and Cash Flow",
    description: "Connect operating performance, cash flow, and intrinsic value.",
    level: "intermediate",
    competency: "valuation",
    estimated_minutes: 45,
    prerequisites: ["financial-statements-foundations"],
    status: "not_started",
    score: null,
    completed_at: null,
    path_state: "recommended",
    path_reason: "Continue with Valuation and Cash Flow; its prerequisite lessons are complete.",
  },
];

const hub: EducationHubData = {
  completed_lessons: 1,
  total_lessons: 2,
  assessed_lessons: 1,
  completion_percent: 50,
  average_score: 90,
  mastery_percent: 72,
  proficiency_band: "proficient",
  recommended_lesson_slug: "valuation-and-cash-flow",
  recommendation_reason: "Continue with Valuation and Cash Flow; its prerequisite lessons are complete.",
  lessons,
  competencies: [
    {
      competency: "financial-statements",
      completed_lessons: 1,
      total_lessons: 1,
      assessed_lessons: 1,
      average_score: 90,
      mastery_percent: 94,
      proficiency_band: "expert",
    },
  ],
};

const assessment: AdaptiveAssessment = {
  lesson_slug: "valuation-and-cash-flow",
  competency: "valuation",
  difficulty: "foundation",
  difficulty_reason: "Foundation difficulty selected because mastery is 0%.",
  question: {
    id: "valuation-foundation-1",
    prompt: "What does discounted cash-flow analysis estimate?",
    options: ["Intrinsic value from future cash flows", "Historical book value only"],
    objective: "Explain the purpose of discounted cash-flow valuation.",
  },
};

const attempts: AssessmentAttempt[] = [
  {
    id: 2,
    lesson_slug: "financial-statements-foundations",
    competency: "financial-statements",
    difficulty: "intermediate",
    question_id: "financials-intermediate-1",
    selected_option: 1,
    score: 100,
    passed: true,
    created_at: "2026-07-19T16:00:00Z",
  },
  {
    id: 1,
    lesson_slug: "financial-statements-foundations",
    competency: "financial-statements",
    difficulty: "foundation",
    question_id: "financials-foundation-1",
    selected_option: 0,
    score: 0,
    passed: false,
    created_at: "2026-07-19T15:00:00Z",
  },
];

function response(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

function routeAwareFetch(historyBody: unknown = attempts, historyStatus = 200) {
  return vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/education") return response(hub);
    if (url === "/api/education/assessment/history") return response(historyBody, historyStatus);
    return response(null, 404);
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("EducationHub", () => {
  it("renders private passed and remediation mastery evidence without answer-key data", async () => {
    const fetchMock = routeAwareFetch();
    vi.stubGlobal("fetch", fetchMock);

    render(<EducationHub />);

    const history = await screen.findByLabelText("Mastery history");
    expect(within(history).getByText("2 attempts")).toBeInTheDocument();
    expect(within(history).getByText("100% · Passed")).toBeInTheDocument();
    expect(within(history).getByText("0% · Needs review")).toBeInTheDocument();
    expect(within(history).getByText("mastery")).toBeInTheDocument();
    expect(within(history).getByText("remediation")).toBeInTheDocument();
    expect(screen.queryByText(/correct option/i)).not.toBeInTheDocument();
    expect(JSON.stringify(fetchMock.mock.calls)).not.toContain("correct_option");
  });

  it("shows an empty history state without blocking the learning path", async () => {
    vi.stubGlobal("fetch", routeAwareFetch([]));
    render(<EducationHub />);

    expect(await screen.findByText("No assessment attempts yet. Your competency checks will appear here.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Begin assessment" })).toBeEnabled();
  });

  it("degrades gracefully when mastery history is unavailable", async () => {
    vi.stubGlobal("fetch", routeAwareFetch({ detail: "unavailable" }, 503));
    render(<EducationHub />);

    expect(await screen.findByText("Mastery history is temporarily unavailable. Your lessons and assessments remain available.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry mastery history" })).toBeEnabled();
    expect(screen.getByLabelText("72% mastery")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Begin assessment" })).toBeEnabled();
  });

  it("retries mastery history in place and disables duplicate recovery requests", async () => {
    const user = userEvent.setup();
    let historyCalls = 0;
    let resolveRetry: ((value: { ok: boolean; status: number; json: () => Promise<unknown> }) => void) | undefined;
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/education") return response(hub);
      if (url === "/api/education/assessment/history") {
        historyCalls += 1;
        if (historyCalls === 1) return response({ detail: "unavailable" }, 503);
        return new Promise<{ ok: boolean; status: number; json: () => Promise<unknown> }>((resolve) => {
          resolveRetry = resolve;
        });
      }
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<EducationHub />);

    const retry = await screen.findByRole("button", { name: "Retry mastery history" });
    await user.click(retry);

    expect(screen.getByRole("button", { name: "Retrying…" })).toBeDisabled();
    expect(historyCalls).toBe(2);

    resolveRetry?.(await response(attempts));

    const history = await screen.findByLabelText("Mastery history");
    await waitFor(() => expect(within(history).getByText("2 attempts")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Retry mastery history" })).not.toBeInTheDocument();
    expect(within(history).getByText("100% · Passed")).toBeInTheDocument();
  });

  it("refreshes mastery history after a scored assessment", async () => {
    const user = userEvent.setup();
    const refreshedAttempt: AssessmentAttempt = {
      id: 3,
      lesson_slug: "valuation-and-cash-flow",
      competency: "valuation",
      difficulty: "foundation",
      question_id: assessment.question.id,
      selected_option: 0,
      score: 100,
      passed: true,
      created_at: "2026-07-19T17:00:00Z",
    };
    const result: AssessmentResult = {
      lesson_slug: "valuation-and-cash-flow",
      competency: "valuation",
      difficulty: "foundation",
      score: 100,
      passed: true,
      feedback: "Mastery demonstrated for valuation.",
      learning_objective: assessment.question.objective,
      education_hub: { ...hub, mastery_percent: 90, proficiency_band: "expert" },
    };
    let historyCalls = 0;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/education") return response(hub);
      if (url === "/api/education/assessment/history") {
        historyCalls += 1;
        return response(historyCalls === 1 ? attempts : [refreshedAttempt, ...attempts]);
      }
      if (url === "/api/education/assessment" && init?.method === "POST") return response(result);
      if (url === "/api/education/assessment") return response(assessment);
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<EducationHub />);
    await user.click(await screen.findByRole("button", { name: "Begin assessment" }));
    await user.click(await screen.findByLabelText("Intrinsic value from future cash flows"));
    await user.click(screen.getByRole("button", { name: "Submit assessment" }));

    const resultCard = screen.getByLabelText("Adaptive competency assessment");
    expect(await within(resultCard).findByText("100% · Passed")).toBeInTheDocument();
    await waitFor(() => expect(historyCalls).toBe(2));
    const history = screen.getByLabelText("Mastery history");
    expect(within(history).getByText("3 attempts")).toBeInTheDocument();
    expect(within(history).getByText("Valuation and Cash Flow")).toBeInTheDocument();
    expect(screen.getByLabelText("90% mastery")).toBeInTheDocument();
  });

  it("starts a recommended lesson without offering manual completion", async () => {
    const user = userEvent.setup();
    const updated = {
      ...hub,
      lessons: hub.lessons.map((lesson) =>
        lesson.slug === "valuation-and-cash-flow" ? { ...lesson, status: "in_progress" } : lesson,
      ),
    };
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/education") return response(hub);
      if (url === "/api/education/assessment/history") return response([]);
      if (url.includes("/progress")) return response(updated);
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<EducationHub />);
    const card = await screen.findByLabelText("Valuation and Cash Flow: recommended");
    await user.click(within(card).getByRole("button", { name: "Start lesson" }));

    await waitFor(() => expect(within(card).getByRole("button", { name: "Take competency check" })).toBeInTheDocument());
    expect(within(card).queryByRole("button", { name: "Complete lesson" })).not.toBeInTheDocument();
  });
});
