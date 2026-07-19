import React from "react";
import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CompetencyTrends } from "@/components/competency-trends";

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

describe("CompetencyTrends", () => {
  it("renders explainable improving and insufficient-evidence trends without answer keys", async () => {
    const trends = [
      {
        competency: "evidence-evaluation",
        attempt_count: 4,
        recent_average: 100,
        prior_average: 50,
        direction: "improving",
        explanation: "Recent performance is 50 points above the prior comparison window.",
      },
      {
        competency: "research-reasoning",
        attempt_count: 2,
        recent_average: 50,
        prior_average: null,
        direction: "insufficient_evidence",
        explanation: "Four attempts are required before a trend is declared.",
      },
    ];
    const fetchMock = vi.fn(() => response(trends));
    vi.stubGlobal("fetch", fetchMock);

    render(<CompetencyTrends />);

    const panel = await screen.findByLabelText("Competency trends");
    expect(within(panel).getByText("improving")).toBeInTheDocument();
    expect(within(panel).getByText("insufficient evidence")).toBeInTheDocument();
    expect(within(panel).getByText(/recent 100% · prior 50%/)).toBeInTheDocument();
    expect(within(panel).getByText(/recent 50% · prior —/)).toBeInTheDocument();
    expect(JSON.stringify(fetchMock.mock.calls)).not.toContain("correct_option");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/education/assessment/trends",
      expect.objectContaining({ cache: "no-store", signal: expect.any(AbortSignal) }),
    );
  });

  it("degrades gracefully when trend insights are unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({ detail: "unavailable" }, 503)));

    render(<CompetencyTrends />);

    expect(
      await screen.findByText("Competency trends are temporarily unavailable. Your lessons and assessments remain available."),
    ).toBeInTheDocument();
  });

  it("shows an empty state when no assessment evidence exists", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response([])));

    render(<CompetencyTrends />);

    expect(await screen.findByText("No assessment evidence is available yet.")).toBeInTheDocument();
  });
});
