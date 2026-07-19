import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ResearchLearningRecommendations } from "@/components/research-learning-recommendations";

const payload = {
  investigation_id: 4,
  recommendation_count: 2,
  completion_authority: "adaptive_assessment_only",
  recommendations: [
    {
      competency: "evidence-evaluation",
      lesson_slug: "evidence-quality-and-bias",
      lesson_title: "Evidence Quality and Bias",
      gap_type: "contradictory_evidence",
      priority: 1,
      reason: "Contradictory evidence requires source-quality review before confidence can increase.",
    },
    {
      competency: "research-reasoning",
      lesson_slug: "research-thesis-construction",
      lesson_title: "Research Thesis Construction",
      gap_type: "unresolved_questions",
      priority: 2,
      reason: "Unresolved questions indicate that assumptions and falsification criteria need refinement.",
    },
  ],
};

describe("ResearchLearningRecommendations", () => {
  beforeEach(() => vi.unstubAllGlobals());

  it("shows explainable recommendations without claiming lesson completion", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 })));
    render(<ResearchLearningRecommendations investigationId={4} />);

    fireEvent.click(screen.getByRole("button", { name: "Analyze learning gaps" }));

    expect(await screen.findByText("Evidence Quality and Bias")).toBeInTheDocument();
    expect(screen.getByText("Research Thesis Construction")).toBeInTheDocument();
    expect(screen.getByText(/Contradictory evidence requires/)).toBeInTheDocument();
    expect(screen.getByText("Completion authority: adaptive assessment only.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open lesson in Education Hub" })).toHaveAttribute(
      "href",
      "/education#evidence-quality-and-bias",
    );
    expect(screen.queryByText(/correct option/i)).not.toBeInTheDocument();
  });

  it("shows a no-gap state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            investigation_id: 4,
            recommendation_count: 0,
            completion_authority: "adaptive_assessment_only",
            recommendations: [],
          }),
          { status: 200 },
        ),
      ),
    );
    render(<ResearchLearningRecommendations investigationId={4} />);

    fireEvent.click(screen.getByRole("button", { name: "Analyze learning gaps" }));
    expect(await screen.findByText("No research-learning gaps were identified.")).toBeInTheDocument();
  });

  it("contains recommendation failure locally", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 503 })));
    render(<ResearchLearningRecommendations investigationId={4} />);

    fireEvent.click(screen.getByRole("button", { name: "Analyze learning gaps" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Education Hub remain available");
    expect(screen.getByText("Learning recommendations")).toBeInTheDocument();
  });
});
