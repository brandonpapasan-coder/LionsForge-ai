import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { KnowledgeQualityDashboard } from "@/components/knowledge-quality-dashboard";
import type { KnowledgeQualityDashboard as KnowledgeQualityDashboardData } from "@/lib/knowledge-quality";

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

function dashboard(projectId: number | null, healthScore: number): KnowledgeQualityDashboardData {
  return {
    project_id: projectId,
    methodology_version: "knowledge-quality-v1",
    generated_at: "2026-07-17T12:00:00Z",
    health_score: healthScore,
    health_components: { validation: healthScore },
    memories: {
      total: 1,
      validated: 1,
      provisional: 0,
      contested: 0,
      superseded: 0,
      archived: 0,
      stale: 0,
    },
    evidence_total: 1,
    evidence_approved: 1,
    evidence_pending_review: 0,
    evidence_coverage_ratio: 1,
    average_confidence: healthScore,
    median_confidence: healthScore,
    contradiction_rate: 0,
    unresolved_contradictions: 0,
    federation_links: 0,
    federation_coverage_ratio: 0,
    missions: {},
    planning: {},
    knowledge_revision_velocity: 0,
    review_backlog: 0,
    top_risks: [],
    top_priorities: [],
    recent_activity: [],
  };
}

const projects = [
  {
    id: 7,
    title: "Grid Storage Study",
    description: null,
    objective: null,
    status: "active",
    context: {},
    created_at: "2026-07-17T10:00:00Z",
    updated_at: "2026-07-17T11:00:00Z",
  },
  {
    id: 8,
    title: "Advanced Materials Study",
    description: null,
    objective: null,
    status: "active",
    context: {},
    created_at: "2026-07-17T10:00:00Z",
    updated_at: "2026-07-17T11:00:00Z",
  },
];

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("KnowledgeQualityDashboard mounted-state ownership", () => {
  it("ignores a late dashboard error response after unmount", async () => {
    const dashboardResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let dashboardSignal: AbortSignal | undefined;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/research-projects") return response([]);
      if (url === "/api/knowledge-quality") {
        dashboardSignal = init?.signal ?? undefined;
        return dashboardResponse.promise;
      }
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const { unmount } = render(<KnowledgeQualityDashboard />);
    await waitFor(() => expect(dashboardSignal).toBeDefined());

    unmount();
    expect(dashboardSignal?.aborted).toBe(true);

    dashboardResponse.resolve(await response(null, 404));
    await Promise.resolve();
    await Promise.resolve();

    expect(consoleError).not.toHaveBeenCalled();
  });

  it("does not start organization loading after project discovery is aborted", async () => {
    const projectsResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let projectsSignal: AbortSignal | undefined;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/research-projects") {
        projectsSignal = init?.signal ?? undefined;
        return projectsResponse.promise;
      }
      return response(null, 500);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<KnowledgeQualityDashboard />);
    await waitFor(() => expect(projectsSignal).toBeDefined());
    unmount();

    projectsResponse.resolve(await response([]));
    await Promise.resolve();
    await Promise.resolve();

    expect(projectsSignal?.aborted).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("keeps the newest successful scope when a superseded request fails late", async () => {
    const staleResponse = deferred<Awaited<ReturnType<typeof response>>>();
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/research-projects") return response(projects);
      if (url === "/api/knowledge-quality") return response(dashboard(null, 0.82));
      if (url === "/api/knowledge-quality/projects/7") return staleResponse.promise;
      if (url === "/api/knowledge-quality/projects/8") return response(dashboard(8, 0.91));
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<KnowledgeQualityDashboard />);
    await screen.findByText("82%");

    const selector = screen.getByRole("combobox", { name: "Knowledge scope" });
    fireEvent.change(selector, { target: { value: "7" } });
    fireEvent.change(selector, { target: { value: "8" } });

    expect(await screen.findByText("91%")).toBeInTheDocument();
    expect(screen.getByText(/Project: Advanced Materials Study/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Refreshing knowledge health…")).not.toBeInTheDocument());

    staleResponse.resolve(await response(null, 500));
    await Promise.resolve();
    await Promise.resolve();

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText("91%")).toBeInTheDocument();
    expect(screen.queryByText("Refreshing knowledge health…")).not.toBeInTheDocument();
  });
});
