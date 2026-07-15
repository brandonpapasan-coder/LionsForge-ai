import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { KnowledgeQualityDashboard } from "@/components/knowledge-quality-dashboard";
import type { KnowledgeQualityDashboard as KnowledgeQualityDashboardData } from "@/lib/knowledge-quality";

const dashboard: KnowledgeQualityDashboardData = {
  project_id: null,
  methodology_version: "knowledge-quality-v1",
  generated_at: "2026-07-13T20:00:00Z",
  health_score: 0.82,
  health_components: {
    validation: 0.9,
    confidence: 0.8,
    evidence_coverage: 0.75,
  },
  memories: {
    total: 10,
    validated: 7,
    provisional: 2,
    contested: 1,
    superseded: 0,
    archived: 0,
    stale: 1,
  },
  evidence_total: 12,
  evidence_approved: 9,
  evidence_pending_review: 3,
  evidence_coverage_ratio: 0.75,
  average_confidence: 0.8,
  median_confidence: 0.81,
  contradiction_rate: 0.1,
  unresolved_contradictions: 1,
  federation_links: 4,
  federation_coverage_ratio: 0.4,
  missions: {},
  planning: {},
  knowledge_revision_velocity: 3,
  review_backlog: 3,
  top_risks: [
    {
      risk_type: "contested_knowledge",
      severity: 0.7,
      title: "Contested knowledge requires review",
      detail: "One contested record remains visible.",
      source_ids: [4],
    },
  ],
  top_priorities: [],
  recent_activity: [
    {
      record_type: "knowledge_memory",
      record_id: 4,
      title: "Battery storage finding",
      status: "validated",
      occurred_at: "2026-07-13T19:00:00Z",
    },
  ],
};

const projects = [
  {
    id: 7,
    title: "Grid Storage Study",
    description: null,
    objective: null,
    status: "active",
    context: {},
    created_at: "2026-07-12T20:00:00Z",
    updated_at: "2026-07-13T20:00:00Z",
  },
  {
    id: 8,
    title: "Advanced Materials Study",
    description: null,
    objective: null,
    status: "active",
    context: {},
    created_at: "2026-07-12T20:00:00Z",
    updated_at: "2026-07-13T20:00:00Z",
  },
];

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

function successfulFetch(projectDashboard: KnowledgeQualityDashboardData = dashboard) {
  return vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/research-projects") return response(projects);
    if (url === "/api/knowledge-quality") return response(dashboard);
    if (url === "/api/knowledge-quality/projects/7") return response(projectDashboard);
    return response(null, 404);
  });
}

function selectProject(projectId = "7") {
  fireEvent.change(screen.getByRole("combobox", { name: "Knowledge scope" }), {
    target: { value: projectId },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("KnowledgeQualityDashboard", () => {
  it("renders transparent organization-wide metrics, risks, and activity", async () => {
    vi.stubGlobal("fetch", successfulFetch());

    render(<KnowledgeQualityDashboard />);

    expect(await screen.findByText("82%")).toBeInTheDocument();
    expect(screen.getByText("Contested knowledge requires review")).toBeInTheDocument();
    expect(screen.getByText("Battery storage finding")).toBeInTheDocument();
    expect(screen.getByText(/does not validate research/i)).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Knowledge scope" })).toBeInTheDocument();
  });

  it("loads project-scoped quality when an owned project is selected", async () => {
    const projectDashboard: KnowledgeQualityDashboardData = { ...dashboard, project_id: 7, health_score: 0.64 };
    const fetchMock = successfulFetch(projectDashboard);
    vi.stubGlobal("fetch", fetchMock);

    render(<KnowledgeQualityDashboard />);
    await screen.findByText("82%");
    selectProject();

    expect(await screen.findByText("64%")).toBeInTheDocument();
    expect(screen.getByText(/Project: Grid Storage Study/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/knowledge-quality/projects/7",
      expect.objectContaining({ cache: "no-store", signal: expect.any(AbortSignal) }),
    );
  });

  it("keeps the newest scope when an older request finishes last", async () => {
    const firstProjectResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let firstProjectSignal: AbortSignal | undefined;
    const secondProjectDashboard: KnowledgeQualityDashboardData = {
      ...dashboard,
      project_id: 8,
      health_score: 0.91,
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/research-projects") return response(projects);
      if (url === "/api/knowledge-quality") return response(dashboard);
      if (url === "/api/knowledge-quality/projects/7") {
        firstProjectSignal = init?.signal ?? undefined;
        return firstProjectResponse.promise;
      }
      if (url === "/api/knowledge-quality/projects/8") return response(secondProjectDashboard);
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<KnowledgeQualityDashboard />);
    await screen.findByText("82%");

    selectProject("7");
    selectProject("8");

    expect(await screen.findByText("91%")).toBeInTheDocument();
    expect(screen.getByText(/Project: Advanced Materials Study/i)).toBeInTheDocument();
    expect(firstProjectSignal?.aborted).toBe(true);

    firstProjectResponse.resolve(await response({ ...dashboard, project_id: 7, health_score: 0.64 }));
    await waitFor(() => expect(screen.queryByText("64%")).not.toBeInTheDocument());
    expect(screen.getByText("91%")).toBeInTheDocument();
  });

  it("aborts an active dashboard request when unmounted", async () => {
    const organizationResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let organizationSignal: AbortSignal | undefined;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/research-projects") return response(projects);
      if (url === "/api/knowledge-quality") {
        organizationSignal = init?.signal ?? undefined;
        return organizationResponse.promise;
      }
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<KnowledgeQualityDashboard />);
    await waitFor(() => expect(organizationSignal).toBeDefined());

    unmount();
    expect(organizationSignal?.aborted).toBe(true);
  });

  it("shows an honest no-baseline state for empty data", async () => {
    vi.stubGlobal("fetch", successfulFetch({
      ...dashboard,
      health_score: 0,
      memories: { ...dashboard.memories, total: 0, validated: 0, provisional: 0, contested: 0 },
      evidence_total: 0,
      evidence_approved: 0,
      evidence_pending_review: 0,
      top_risks: [],
      recent_activity: [],
    }));

    render(<KnowledgeQualityDashboard />);
    await screen.findByText("82%");
    selectProject();

    expect(await screen.findByText("No baseline")).toBeInTheDocument();
    expect(screen.getByText(/No research baseline exists for this scope yet/i)).toBeInTheDocument();
  });

  it("shows a safe not-found message for inaccessible projects", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/research-projects") return response(projects);
      if (url === "/api/knowledge-quality") return response(dashboard);
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<KnowledgeQualityDashboard />);
    await screen.findByText("82%");
    selectProject();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "That research project could not be found or is not available to this account.",
    );
  });

  it("exposes organization dashboard API failures through an alert", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/research-projects") return response([]);
      return response(null, 500);
    }));

    render(<KnowledgeQualityDashboard />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Institutional knowledge quality could not be loaded.");
    });
  });

  it("handles unauthorized responses without exposing dashboard data", async () => {
    const navigationError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const fetchMock = vi.fn(() => response(null, 401));
    vi.stubGlobal("fetch", fetchMock);

    const { container } = render(<KnowledgeQualityDashboard />);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/knowledge-quality",
        expect.objectContaining({ cache: "no-store", signal: expect.any(AbortSignal) }),
      );
    });
    expect(screen.queryByText("82%")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(container).toBeEmptyDOMElement();
    navigationError.mockRestore();
  });

  it("allows keyboard users to reach and operate the knowledge-scope selector", async () => {
    const user = userEvent.setup();
    const projectDashboard: KnowledgeQualityDashboardData = { ...dashboard, project_id: 7, health_score: 0.64 };
    vi.stubGlobal("fetch", successfulFetch(projectDashboard));

    render(<KnowledgeQualityDashboard />);
    await screen.findByText("82%");

    const selector = screen.getByRole("combobox", { name: "Knowledge scope" });
    await user.tab();
    expect(selector).toHaveFocus();
    await user.selectOptions(selector, "7");

    expect(await screen.findByText("64%")).toBeInTheDocument();
    expect(selector).toHaveValue("7");
  });
});
