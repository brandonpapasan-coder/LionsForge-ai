import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MarketLearningMasteryPanel } from "@/components/market-learning-mastery-panel";
import type { MarketLearningMastery } from "@/lib/market-learning-mastery";

const assessment: MarketLearningMastery = {
  overall_readiness: "developing",
  dimensions_met: 3,
  dimensions_total: 6,
  calculation_criteria: [
    "Each rubric dimension uses deterministic count and quality thresholds.",
    "Simulated returns, gains, losses, and portfolio outcomes are excluded from every assessment rule.",
  ],
  dimensions: [
    {
      key: "scenario_breadth",
      title: "Scenario breadth",
      status: "met",
      evidence_count: 4,
      target_count: 4,
      criteria: "Complete at least four distinct simulated scenarios.",
      unmet_criteria: [],
      next_action: "Complete a scenario not yet represented.",
    },
    {
      key: "review_follow_through",
      title: "Review follow-through",
      status: "developing",
      evidence_count: 2,
      target_count: 3,
      criteria: "Complete immutable review activity for at least three learning claims.",
      unmet_criteria: ["Current evidence: 2; target: 3."],
      next_action: "Review an unreviewed claim.",
    },
  ],
  disclaimer: "This assessment summarizes simulated educational practice only. It is not investment-performance evidence, predictive validation, accreditation, professional certification, employability validation, or financial advice.",
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

describe("MarketLearningMasteryPanel", () => {
  it("renders readiness, rubric dimensions, improvement actions, and safety language", async () => {
    const fetchMock = vi.fn(() => response(assessment));
    vi.stubGlobal("fetch", fetchMock);

    render(<MarketLearningMasteryPanel />);

    expect(await screen.findByText("developing")).toBeInTheDocument();
    expect(screen.getByText("3 of 6 dimensions met")).toBeInTheDocument();
    expect(screen.getByText("Scenario breadth")).toBeInTheDocument();
    expect(screen.getByText("Current evidence: 2; target: 3.")).toBeInTheDocument();
    expect(screen.getByText("not investment-performance evidence", { exact: false })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/market-simulator/learning-mastery",
      expect.objectContaining({ cache: "no-store", signal: expect.any(AbortSignal) }),
    );
  });

  it("renders the not-started state", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({
      ...assessment,
      overall_readiness: "not_started",
      dimensions_met: 0,
      dimensions: assessment.dimensions.map((dimension) => ({
        ...dimension,
        status: "not_started",
        evidence_count: 0,
      })),
    })));

    render(<MarketLearningMasteryPanel />);

    expect(await screen.findByText("Complete your first guided simulation.")).toBeInTheDocument();
  });

  it("aborts the mastery request when unmounted", async () => {
    let requestSignal: AbortSignal | undefined;
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      requestSignal = init?.signal ?? undefined;
      return new Promise(() => undefined);
    }));

    const { unmount } = render(<MarketLearningMasteryPanel />);
    await waitFor(() => expect(requestSignal).toBeDefined());
    unmount();
    expect(requestSignal?.aborted).toBe(true);
  });

  it("shows a safe service error", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response(null, 503)));

    render(<MarketLearningMasteryPanel />);

    expect(await screen.findByRole("alert")).toHaveTextContent("The market learning mastery assessment could not be loaded.");
  });
});
