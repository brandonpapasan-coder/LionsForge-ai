import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchConclusionReadiness } from "@/components/research-conclusion-readiness";

const projects = [
  {
    id: 7,
    title: "Evidence Review",
    description: null,
    objective: "Review evidence",
    status: "active",
    context: {},
    created_at: "2026-07-16T00:00:00Z",
    updated_at: "2026-07-16T00:00:00Z",
  },
  {
    id: 8,
    title: "Second Project",
    description: null,
    objective: "Compare readiness",
    status: "active",
    context: {},
    created_at: "2026-07-16T00:00:00Z",
    updated_at: "2026-07-16T00:00:00Z",
  },
];

const readiness = {
  project_id: 7,
  state: "blocked",
  evidence_count: 2,
  blocking_count: 1,
  caution_count: 1,
  disclaimer: "Workflow completeness only.",
  next_steps: ["Resolve the high-attention action."],
  checks: [
    {
      code: "high_attention_actions_cleared",
      level: "blocking",
      passed: false,
      message: "High-attention review actions must be resolved or dismissed.",
      evidence_ids: [4],
      action_ids: [11],
      event_ids: ["evidence:4"],
      governing_rules: ["evidence_removed"],
    },
  ],
};

const response = (body: unknown, status = 200) =>
  Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body });

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("ResearchConclusionReadiness", () => {
  it("renders state, next steps, and provenance drill-downs", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) =>
        String(input) === "/api/research-projects" ? response(projects) : response(readiness),
      ),
    );

    render(<ResearchConclusionReadiness />);

    expect(await screen.findByText("Conclusion readiness")).toBeInTheDocument();
    expect(await screen.findByText("Blocked")).toBeInTheDocument();
    expect(screen.getByText("Resolve the high-attention action.")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Traceability"));
    expect(screen.getByText(/evidence:4/)).toBeInTheDocument();
    expect(screen.getByText(/evidence_removed/)).toBeInTheDocument();
  });

  it("reloads readiness when the selected project changes", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) =>
      String(input) === "/api/research-projects" ? response(projects) : response(readiness),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<ResearchConclusionReadiness />);
    await screen.findByText("Conclusion readiness");
    fireEvent.change(screen.getByLabelText("Readiness project"), { target: { value: "8" } });

    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/projects/8"))).toBe(true),
    );
  });

  it("surfaces readiness failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) =>
        String(input) === "/api/research-projects" ? response(projects) : response({}, 500),
      ),
    );

    render(<ResearchConclusionReadiness />);
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be loaded");
  });
});
