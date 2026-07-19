import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EducationHub } from "@/components/education-hub";
import type { AdaptiveAssessment, AssessmentResult, EducationHubData, Lesson } from "@/lib/education";

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
    path_reason: "Lesson completed with a recorded assessment score.",
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
  {
    slug: "evidence-quality-and-bias",
    title: "Evidence Quality and Bias",
    description: "Evaluate evidence quality and challenge unsupported assumptions.",
    level: "foundation",
    competency: "evidence-evaluation",
    estimated_minutes: 30,
    prerequisites: [],
    status: "not_started",
    score: null,
    completed_at: null,
    path_state: "available",
    path_reason: "All prerequisites are complete; this lesson is available.",
  },
  {
    slug: "research-thesis-construction",
    title: "Research Thesis Construction",
    description: "Build falsifiable theses with explicit assumptions and risks.",
    level: "intermediate",
    competency: "research-reasoning",
    estimated_minutes: 40,
    prerequisites: ["evidence-quality-and-bias"],
    status: "not_started",
    score: null,
    completed_at: null,
    path_state: "locked",
    path_reason: "Complete Evidence Quality and Bias to unlock this lesson.",
  },
];

const hub: EducationHubData = {
  completed_lessons: 1,
  total_lessons: 4,
  assessed_lessons: 1,
  completion_percent: 25,
  average_score: 90,
  mastery_percent: 64,
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
    {
      competency: "valuation",
      completed_lessons: 0,
      total_lessons: 1,
      assessed_lessons: 0,
      average_score: null,
      mastery_percent: 0,
      proficiency_band: "foundation",
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
    options: ["Intrinsic value from future cash flows", "Historical book value only", "Daily trading volume"],
    objective: "Explain the purpose of discounted cash-flow valuation.",
  },
};

function response(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

function lessonCard(title: string) {
  return screen.getByLabelText(new RegExp(`^${title}:`));
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("EducationHub", () => {
  it("renders mastery, recommendations, prerequisites, and path states", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response(hub)));
    render(<EducationHub />);

    expect(await screen.findByLabelText("64% mastery")).toBeInTheDocument();
    expect(screen.getByText("proficient mastery")).toBeInTheDocument();
    expect(screen.getAllByText("Valuation and Cash Flow")).toHaveLength(2);
    expect(lessonCard("Valuation and Cash Flow")).toHaveAttribute("data-path-state", "recommended");
    expect(within(lessonCard("Research Thesis Construction")).getByRole("button", { name: "Complete prerequisites" })).toBeDisabled();
    expect(screen.getByText(/Passing this check is the only way to complete a lesson/)).toBeInTheDocument();
  });

  it("starts a lesson, then requires its competency check instead of offering manual completion", async () => {
    const user = userEvent.setup();
    const updated: EducationHubData = {
      ...hub,
      lessons: hub.lessons.map((lesson) =>
        lesson.slug === "valuation-and-cash-flow" ? { ...lesson, status: "in_progress" } : lesson,
      ),
    };
    const fetchMock = vi.fn().mockImplementationOnce(() => response(hub)).mockImplementationOnce(() => response(updated));
    vi.stubGlobal("fetch", fetchMock);

    render(<EducationHub />);
    const recommended = await screen.findByLabelText("Valuation and Cash Flow: recommended");
    await user.click(within(recommended).getByRole("button", { name: "Start lesson" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenLastCalledWith(
        "/api/education/lessons/valuation-and-cash-flow/progress",
        expect.objectContaining({
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ status: "in_progress", score: null }),
          signal: expect.any(AbortSignal),
        }),
      );
    });
    expect(within(recommended).queryByRole("button", { name: "Complete lesson" })).not.toBeInTheDocument();
    expect(within(recommended).getByRole("button", { name: "Take competency check" })).toBeInTheDocument();
  });

  it("keeps the newest lesson mutation when an older response finishes last", async () => {
    const user = userEvent.setup();
    const firstMutation = deferred<Awaited<ReturnType<typeof response>>>();
    let firstSignal: AbortSignal | undefined;
    const newestHub: EducationHubData = {
      ...hub,
      lessons: hub.lessons.map((lesson) =>
        lesson.slug === "evidence-quality-and-bias" ? { ...lesson, status: "in_progress" } : lesson,
      ),
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/education") return response(hub);
      if (url.includes("valuation-and-cash-flow")) {
        firstSignal = init?.signal ?? undefined;
        return firstMutation.promise;
      }
      if (url.includes("evidence-quality-and-bias")) return response(newestHub);
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<EducationHub />);
    await screen.findByLabelText("64% mastery");
    await user.click(within(lessonCard("Valuation and Cash Flow")).getByRole("button", { name: "Start lesson" }));
    await user.click(within(lessonCard("Evidence Quality and Bias")).getByRole("button", { name: "Start lesson" }));

    await waitFor(() => expect(firstSignal?.aborted).toBe(true));
    expect(within(lessonCard("Evidence Quality and Bias")).getByRole("button", { name: "Take competency check" })).toBeInTheDocument();
    firstMutation.resolve(await response({ ...hub, mastery_percent: 10 }));
    await waitFor(() => expect(screen.queryByLabelText("10% mastery")).not.toBeInTheDocument());
  });

  it("loads and submits an explainable adaptive assessment", async () => {
    const user = userEvent.setup();
    const updatedHub: EducationHubData = {
      ...hub,
      completed_lessons: 4,
      assessed_lessons: 4,
      completion_percent: 100,
      average_score: 98,
      mastery_percent: 99,
      proficiency_band: "expert",
      recommended_lesson_slug: null,
      recommendation_reason: "All current lessons are complete.",
      lessons: hub.lessons.map((lesson) => ({
        ...lesson,
        status: "completed",
        score: lesson.score ?? 100,
        completed_at: lesson.completed_at ?? "2026-07-14T21:00:00Z",
        path_state: "completed" as const,
        path_reason: "Lesson completed with a recorded assessment score.",
      })),
    };
    const result: AssessmentResult = {
      lesson_slug: "valuation-and-cash-flow",
      competency: "valuation",
      difficulty: "foundation",
      score: 100,
      passed: true,
      feedback: "Mastery demonstrated for valuation.",
      learning_objective: assessment.question.objective,
      education_hub: updatedHub,
    };
    const fetchMock = vi.fn().mockImplementationOnce(() => response(hub)).mockImplementationOnce(() => response(assessment)).mockImplementationOnce(() => response(result));
    vi.stubGlobal("fetch", fetchMock);

    render(<EducationHub />);
    await user.click(await screen.findByRole("button", { name: "Begin assessment" }));
    expect(await screen.findByText(assessment.question.prompt)).toBeInTheDocument();
    await user.click(screen.getByLabelText("Intrinsic value from future cash flows"));
    await user.click(screen.getByRole("button", { name: "Submit assessment" }));

    expect(await screen.findByText("100% · Passed")).toBeInTheDocument();
    expect(screen.getByLabelText("99% mastery")).toBeInTheDocument();
  });

  it("aborts active requests when unmounted", async () => {
    const initial = deferred<Awaited<ReturnType<typeof response>>>();
    let initialSignal: AbortSignal | undefined;
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      initialSignal = init?.signal ?? undefined;
      return initial.promise;
    }));

    const view = render(<EducationHub />);
    await waitFor(() => expect(initialSignal).toBeDefined());
    view.unmount();
    expect(initialSignal?.aborted).toBe(true);
  });

  it("shows the completed path and accessible failures", async () => {
    const completedHub: EducationHubData = {
      ...hub,
      completed_lessons: 4,
      completion_percent: 100,
      recommended_lesson_slug: null,
      recommendation_reason: "All current lessons are complete.",
      lessons: hub.lessons.map((lesson) => ({
        ...lesson,
        status: "completed",
        score: lesson.score ?? 85,
        completed_at: lesson.completed_at ?? "2026-07-14T21:00:00Z",
        path_state: "completed" as const,
        path_reason: "Lesson completed with a recorded assessment score.",
      })),
    };
    vi.stubGlobal("fetch", vi.fn(() => response(completedHub)));
    const view = render(<EducationHub />);
    expect(await screen.findAllByText("Path complete")).toHaveLength(2);
    view.unmount();

    vi.stubGlobal("fetch", vi.fn(() => response(null, 500)));
    render(<EducationHub />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The Education Hub could not be loaded.");
  });
});
