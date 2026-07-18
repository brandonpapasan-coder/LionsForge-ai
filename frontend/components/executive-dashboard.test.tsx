import React from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ExecutiveDashboard } from "@/components/executive-dashboard";
import type { ExecutiveDashboard as ExecutiveDashboardData } from "@/lib/dashboard";

vi.mock("@/components/knowledge-quality-dashboard", () => ({
  KnowledgeQualityDashboard: () => <div>Knowledge quality</div>,
}));

vi.mock("@/components/market-learning-progress-panel", () => ({
  MarketLearningProgressPanel: () => <div>Legacy market learning progress</div>,
}));
vi.mock("@/components/market-learning-roadmap-panel", () => ({
  MarketLearningRoadmapPanel: () => <div>Legacy market learning roadmap</div>,
}));
vi.mock("@/components/market-learning-mastery-panel", () => ({
  MarketLearningMasteryPanel: () => <div>Legacy market learning mastery</div>,
}));
vi.mock("@/components/market-learning-evidence-panel", () => ({
  MarketLearningEvidencePanel: () => <div>Legacy market learning evidence</div>,
}));
vi.mock("@/components/market-learning-portfolio-panel", () => ({
  MarketLearningPortfolioPanel: () => <div>Legacy market learning portfolio</div>,
}));

const dashboard: ExecutiveDashboardData = {
  greeting: "Good morning, Brandon",
  briefing: "Your research and education systems are ready.",
  metrics: [
    { label: "Research projects", value: 4, detail: "Active investigations" },
  ],
  next_actions: [
    { title: "Review evidence", reason: "Validate the latest findings.", href: "/research", priority: "high" },
  ],
  recent_activity: [],
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

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("ExecutiveDashboard request lifecycle", () => {
  it("renders dashboard data from the active request without legacy finance learning panels", async () => {
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      expect(init).toEqual(expect.objectContaining({
        cache: "no-store",
        signal: expect.any(AbortSignal),
      }));
      return response(dashboard);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ExecutiveDashboard />);

    expect(await screen.findByRole("heading", { name: "Good morning, Brandon" })).toBeInTheDocument();
    expect(screen.getByText("Knowledge quality")).toBeInTheDocument();
    expect(screen.queryByText(/Legacy market learning/)).not.toBeInTheDocument();
  });

  it("aborts dashboard loading when unmounted", async () => {
    const dashboardResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let dashboardSignal: AbortSignal | undefined;
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      dashboardSignal = init?.signal ?? undefined;
      return dashboardResponse.promise;
    });
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<ExecutiveDashboard />);
    await waitFor(() => expect(dashboardSignal).toBeDefined());
    unmount();

    expect(dashboardSignal?.aborted).toBe(true);
  });

  it("ignores a late unauthorized response after unmount", async () => {
    const dashboardResponse = deferred<Awaited<ReturnType<typeof response>>>();
    const navigationError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.stubGlobal("fetch", vi.fn(() => dashboardResponse.promise));

    const { unmount } = render(<ExecutiveDashboard />);
    unmount();

    await act(async () => {
      dashboardResponse.resolve(await response(null, 401));
      await dashboardResponse.promise;
    });

    expect(navigationError).not.toHaveBeenCalled();
  });
});
