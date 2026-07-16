import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MarketLearningPortfolioPanel } from "@/components/market-learning-portfolio-panel";
import type { MarketLearningPortfolio } from "@/lib/market-learning-portfolio";

const portfolio: MarketLearningPortfolio = {
  completed_sessions: 6,
  unique_scenarios: 4,
  scenario_counts: { bear_market: 2, high_volatility: 2, inflation_shock: 1, bull_market: 1 },
  risk_tier_counts: { moderate: 4, high: 2 },
  submitted_evidence: 3,
  validation_status_counts: { approved: 1, needs_review: 2 },
  immutable_review_events: 4,
  learning_maturity: "developing",
  maturity_criteria: [
    "6 completed learning sessions",
    "4 distinct scenarios explored",
    "3 learning claims submitted",
    "4 immutable review events",
  ],
  recent_claims: [
    {
      session_id: 10,
      evidence_id: 22,
      scenario_name: "bear_market",
      risk_tier: "high",
      claim: "The simulated exercise indicated that concentration amplified modeled downside risk.",
      validation_status: "needs_review",
      reviewer_notes: "Compare another scenario.",
      review_event_count: 2,
      next_reflection_prompt: "What additional scenario or evidence would help resolve the uncertainty?",
      completed_at: "2026-07-16T01:00:00Z",
    },
  ],
  disclaimer: "This portfolio summarizes simulated educational learning only. It is not a record of investment performance, predictive accuracy, professional certification, real-world empirical validation, or financial advice.",
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

describe("MarketLearningPortfolioPanel", () => {
  it("renders maturity, breadth, validation distribution, recent claims, and safety boundaries", async () => {
    const fetchMock = vi.fn(() => response(portfolio));
    vi.stubGlobal("fetch", fetchMock);

    render(<MarketLearningPortfolioPanel />);

    expect(await screen.findByText("developing")).toBeInTheDocument();
    expect(screen.getByText("6 completed educational simulations")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("not a record of investment performance", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("The simulated exercise indicated that concentration amplified modeled downside risk.")).toBeInTheDocument();
    expect(screen.getByText("Compare another scenario.")).toBeInTheDocument();
    const needsReview = screen.getByText("needs review", { selector: "strong" }).closest("div.activity-card");
    expect(needsReview).not.toBeNull();
    expect(within(needsReview as HTMLElement).getByText("2")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/market-simulator/learning-portfolio",
      expect.objectContaining({ cache: "no-store", signal: expect.any(AbortSignal) }),
    );
  });

  it("renders a guided empty state", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({
      ...portfolio,
      completed_sessions: 0,
      unique_scenarios: 0,
      scenario_counts: {},
      risk_tier_counts: {},
      submitted_evidence: 0,
      validation_status_counts: {},
      immutable_review_events: 0,
      learning_maturity: "not_started",
      maturity_criteria: [
        "0 completed learning sessions",
        "0 distinct scenarios explored",
        "0 learning claims submitted",
        "0 immutable review events",
      ],
      recent_claims: [],
    })));

    render(<MarketLearningPortfolioPanel />);

    expect(await screen.findByText("No market learning portfolio yet.")).toBeInTheDocument();
    expect(screen.getByText("guided simulation and reflection", { exact: false })).toBeInTheDocument();
  });

  it("aborts the portfolio request when unmounted", async () => {
    let requestSignal: AbortSignal | undefined;
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      requestSignal = init?.signal ?? undefined;
      return new Promise(() => undefined);
    }));

    const { unmount } = render(<MarketLearningPortfolioPanel />);
    await waitFor(() => expect(requestSignal).toBeDefined());
    unmount();
    expect(requestSignal?.aborted).toBe(true);
  });

  it("shows a safe service error", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response(null, 503)));

    render(<MarketLearningPortfolioPanel />);

    expect(await screen.findByRole("alert")).toHaveTextContent("The market learning portfolio could not be loaded.");
  });
});
