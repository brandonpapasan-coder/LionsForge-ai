import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EducationHub } from "@/components/education-hub";
import type { AdaptiveAssessment, EducationHubData } from "@/lib/education";

const hub: EducationHubData = {
  completed_lessons: 0,
  total_lessons: 1,
  assessed_lessons: 0,
  completion_percent: 0,
  average_score: null,
  mastery_percent: 0,
  proficiency_band: "foundation",
  recommended_lesson_slug: "financial-statements-foundations",
  recommendation_reason: "Continue the curriculum with the next available foundation lesson.",
  lessons: [
    {
      slug: "financial-statements-foundations",
      title: "Financial Statements Foundations",
      description: "Read financial statements as one connected system.",
      level: "foundation",
      competency: "financial-statements",
      estimated_minutes: 35,
      prerequisites: [],
      status: "in_progress",
      score: null,
      completed_at: null,
      path_state: "recommended",
      path_reason: "Continue the curriculum with the next available foundation lesson.",
    },
  ],
  competencies: [
    {
      competency: "financial-statements",
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
  lesson_slug: "financial-statements-foundations",
  competency: "financial-statements",
  difficulty: "foundation",
  difficulty_reason: "Foundation difficulty selected because mastery is 0%.",
  question: {
    id: "financial-statements-foundation-1",
    prompt: "Which statements form the core financial reporting set?",
    options: ["Income statement, balance sheet, and cash-flow statement", "Only the income statement"],
    objective: "Identify the connected financial statements.",
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

describe("EducationHub completion authority", () => {
  it("routes an in-progress lesson to the adaptive assessment without sending a completion update", async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() => response(hub))
      .mockImplementationOnce(() => response(assessment));
    vi.stubGlobal("fetch", fetchMock);

    render(<EducationHub />);

    const card = await screen.findByLabelText("Financial Statements Foundations: recommended");
    expect(within(card).queryByRole("button", { name: "Complete lesson" })).not.toBeInTheDocument();
    await user.click(within(card).getByRole("button", { name: "Take competency check" }));

    expect(await screen.findByText(assessment.question.prompt)).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/education/assessment",
      expect.objectContaining({ cache: "no-store", signal: expect.any(AbortSignal) }),
    );
    expect(fetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining("/progress"),
      expect.objectContaining({ method: "PUT" }),
    );
  });
});
