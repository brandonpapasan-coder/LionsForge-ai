import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MarketLearningProgressPanel } from "@/components/market-learning-progress-panel";
import type { MarketLearningProgress } from "@/lib/market-learning-progress";

const progress: MarketLearningProgress = {
  total_sessions: 6,
  completed_sessions: 6,
  unique_scenarios: 5,
  scenario_counts: {
    bull_market: 2,
    bear_market: 1,
    high_volatility: 1,
    inflation_shock: 1,
    rate_cut_rally: 1,
  },
  risk_tier_counts: { low: 2, moderate: 3, high: 1 },
  average_projected_return: "0.0475",
  latest_completed_at: "2026-07-15T20:00:00Z",
  proficiency_level: "proficient",
  evidence_badge_eligible: true,
  next_learning_step: "Compare reflections across scenarios.",
  disclaimer: "Educational progress only; not financial advice or an investment-performance score.",
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

describe("MarketLearningProgressPanel", () => {
  it("renders learning level, scenario coverage, badge status, and guardrails", async () => {
    const fetchMock = vi.fn(() => response(progress));
    vi.stubGlobal("fetch", fetchMock);

    render(<MarketLearningProgressPanel />);

    expect(await screen.findByText("proficient")).toBeInTheDocument();
    expect(screen.getByText("5/5")).toBeInTheDocument();
    expect(screen.getByText("Eligible")).toBeInTheDocument();
    expect(screen.getByText("4.8%")).toBeInTheDocument();
    expect(screen.getByText("not financial advice", { exact: false })).toBeInTheDocument();
    const bullCard = screen.getByText("bull market").closest("div.activity-card");
    expect(bullCard).not.toBeNull();
    expect(within(bullCard as HTMLElement).getByText("2")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/market-simulator/learning-progress",
      expect.objectContaining({ cache: "no-store", signal: expect.any(AbortSignal) }),
    );
  });

  it("shows actionable guidance for an empty learning history", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({
      ...progress,
      total_sessions: 0,
      completed_sessions: 0,
      unique_scenarios: 0,
      scenario_counts: {},
      risk_tier_counts: {},
      average_projected_return: "0",
      latest_completed_at: null,
      proficiency_level: "not_started",
      evidence_badge_eligible: false,
    })));

    render(<MarketLearningProgressPanel />);

    expect(await screen.findByText("No completed learning sessions yet.")).toBeInTheDocument();
    expect(screen.getByText("guided market scenario", { exact: false })).toBeInTheDocument();
  });

  it("aborts the progress request when unmounted", async () => {
    let requestSignal: AbortSignal | undefined;
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      requestSignal = init?.signal ?? undefined;
      return new Promise(() => undefined);
    }));

    const { unmount } = render(<MarketLearningProgressPanel />);
    await waitFor(() => expect(requestSignal).toBeDefined());
    unmount();
    expect(requestSignal?.aborted).toBe(true);
  });

  it("shows a safe service error", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response(null, 503)));

    render(<MarketLearningProgressPanel />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Market learning progress could not be loaded.",
    );
  });
});
