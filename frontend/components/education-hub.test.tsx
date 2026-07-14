import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EducationHub } from "@/components/education-hub";
import type { AdaptiveAssessment, AssessmentResult, EducationHubData } from "@/lib/education";

const hub: EducationHubData = {
  completed_lessons: 1,
  total_lessons: 4,
  assessed_lessons: 1,
  completion_percent: 25,
  average_score: 90,
  mastery_percent: 64,
  proficiency_band: "proficient",
  recommended_lesson_slug: "valuation-and-cash-flow",
  recommendation_reason: "Continue the curriculum with the next unfinished lesson.",
  lessons: [
    {
      slug: "financial-statements-foundations",
      title: "Financial Statements Foundations",
      description: "Read financial statements as one connected system.",
      level: "foundation",
      competency: "financial-statements",
      estimated_minutes: 35,
      status: "completed",
      score: 90,
      completed_at: "2026-07-14T19:00:00Z",
    },
    {
      slug: "valuation-and-cash-flow",
      title: "Valuation and Cash Flow",
      description: "Connect operating performance, cash flow, and intrinsic value.",
      level: "intermediate",
      competency: "valuation",
      estimated_minutes: 45,
      status: "not_started",
      score: null,
      completed_at: null,
    },
  ],
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
  difficulty_reason: "Foundation difficulty was selected because valuation mastery is 0%.",
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

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("EducationHub", () => {
  it("renders mastery, recommendation rationale, and competency details", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response(hub)));

    render(<EducationHub />);

    expect(await screen.findByLabelText("64% mastery")).toBeInTheDocument();
    expect(screen.getByText("proficient mastery")).toBeInTheDocument();
    expect(screen.getByText("25%")).toBeInTheDocument();
    expect(screen.getByText("90%")).toBeInTheDocument();
    expect(screen.getAllByText("Valuation and Cash Flow")).toHaveLength(2);
    expect(screen.getByText("Continue the curriculum with the next unfinished lesson.")).toBeInTheDocument();
    expect(screen.getByText("45 minute intermediate lesson")).toBeInTheDocument();
    expect(screen.getByText("expert · 90% average")).toBeInTheDocument();
    expect(screen.getByText("foundation · not assessed")).toBeInTheDocument();
    expect(screen.getByText("recommended")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Begin assessment" })).toBeInTheDocument();
  });

  it("loads and displays an explainable adaptive assessment", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockImplementationOnce(() => response(hub)).mockImplementationOnce(() => response(assessment));
    vi.stubGlobal("fetch", fetchMock);

    render(<EducationHub />);
    await user.click(await screen.findByRole("button", { name: "Begin assessment" }));

    expect(await screen.findByText("What does discounted cash-flow analysis estimate?")).toBeInTheDocument();
    expect(screen.getByLabelText("Adaptive competency assessment")).toHaveTextContent(
      "Foundation difficulty was selected because valuation mastery is 0%.",
    );
    expect(screen.getByText("Explain the purpose of discounted cash-flow valuation.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith("/api/education/assessment", { cache: "no-store" });
  });

  it("submits an assessment and refreshes mastery and feedback", async () => {
    const user = userEvent.setup();
    const updatedHub: EducationHubData = {
      ...hub,
      completed_lessons: 2,
      assessed_lessons: 2,
      completion_percent: 50,
      average_score: 95,
      mastery_percent: 77,
      proficiency_band: "advanced",
      recommended_lesson_slug: null,
      recommendation_reason: "All current lessons are complete.",
      lessons: hub.lessons.map((lesson) =>
        lesson.slug === "valuation-and-cash-flow"
          ? { ...lesson, status: "completed", score: 100, completed_at: "2026-07-14T21:00:00Z" }
          : lesson,
      ),
    };
    const result: AssessmentResult = {
      lesson_slug: "valuation-and-cash-flow",
      competency: "valuation",
      difficulty: "foundation",
      score: 100,
      passed: true,
      feedback: "You demonstrated the stated valuation objective.",
      learning_objective: "Explain the purpose of discounted cash-flow valuation.",
      education_hub: updatedHub,
    };
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() => response(hub))
      .mockImplementationOnce(() => response(assessment))
      .mockImplementationOnce(() => response(result));
    vi.stubGlobal("fetch", fetchMock);

    render(<EducationHub />);
    await user.click(await screen.findByRole("button", { name: "Begin assessment" }));
    await user.click(await screen.findByLabelText("Intrinsic value from future cash flows"));
    await user.click(screen.getByRole("button", { name: "Submit assessment" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenLastCalledWith("/api/education/assessment", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question_id: "valuation-foundation-1", selected_option: 0 }),
      });
    });
    expect(await screen.findByText("100% · Passed")).toBeInTheDocument();
    expect(screen.getByText("You demonstrated the stated valuation objective.")).toBeInTheDocument();
    expect(screen.getByLabelText("77% mastery")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Learning path complete" })).toBeDisabled();
  });

  it("shows a score-aware remediation explanation", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        response({
          ...hub,
          average_score: 55,
          recommendation_reason:
            "Strengthen valuation: your 55% assessment average is below the 70% remediation threshold.",
          lessons: hub.lessons.map((lesson) =>
            lesson.slug === "valuation-and-cash-flow" ? { ...lesson, status: "in_progress", score: 55 } : lesson,
          ),
        }),
      ),
    );

    render(<EducationHub />);

    expect(
      await screen.findByText(
        "Strengthen valuation: your 55% assessment average is below the 70% remediation threshold.",
      ),
    ).toBeInTheDocument();
  });

  it("starts the recommended lesson and refreshes mastery data", async () => {
    const user = userEvent.setup();
    const updated: EducationHubData = {
      ...hub,
      recommended_lesson_slug: "valuation-and-cash-flow",
      lessons: hub.lessons.map((lesson) =>
        lesson.slug === "valuation-and-cash-flow" ? { ...lesson, status: "in_progress" } : lesson,
      ),
    };
    const fetchMock = vi.fn().mockImplementationOnce(() => response(hub)).mockImplementationOnce(() => response(updated));
    vi.stubGlobal("fetch", fetchMock);

    render(<EducationHub />);
    await screen.findByLabelText("64% mastery");
    await user.click(screen.getByRole("button", { name: "Start lesson" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenLastCalledWith(
        "/api/education/lessons/valuation-and-cash-flow/progress",
        {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ status: "in_progress", score: null }),
        },
      );
    });
    expect(await screen.findByRole("button", { name: "Complete lesson" })).toBeInTheDocument();
  });

  it("shows the completed-path state when no lesson remains", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        response({
          ...hub,
          completed_lessons: 4,
          completion_percent: 100,
          recommended_lesson_slug: null,
          recommendation_reason: "All current lessons are complete.",
        }),
      ),
    );

    render(<EducationHub />);

    expect(await screen.findAllByText("Path complete")).toHaveLength(2);
    expect(screen.getByText("All current lessons are complete.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Path complete" })).toBeDisabled();
  });

  it("exposes load, save, and assessment failures through accessible alerts", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response(null, 500)));
    const { unmount } = render(<EducationHub />);

    expect(await screen.findByRole("alert")).toHaveTextContent("The Education Hub could not be loaded.");
    unmount();

    const user = userEvent.setup();
    const saveFetchMock = vi.fn().mockImplementationOnce(() => response(hub)).mockImplementationOnce(() => response(null, 500));
    vi.stubGlobal("fetch", saveFetchMock);
    const saveView = render(<EducationHub />);
    await screen.findByLabelText("64% mastery");
    await user.click(screen.getByRole("button", { name: "Start lesson" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Lesson progress could not be saved.");
    saveView.unmount();

    const assessmentFetchMock = vi
      .fn()
      .mockImplementationOnce(() => response(hub))
      .mockImplementationOnce(() => response(null, 500));
    vi.stubGlobal("fetch", assessmentFetchMock);
    render(<EducationHub />);
    await user.click(await screen.findByRole("button", { name: "Begin assessment" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The adaptive assessment could not be loaded.");
  });
});
