import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchFollowUpQueue } from "@/components/research-follow-up-queue";

const projects = [{ id: 7, title: "Evidence Review", description: null, objective: "Review evidence", status: "active", context: {}, created_at: "2026-07-16T00:00:00Z", updated_at: "2026-07-16T00:00:00Z" }];
const queue = { project_id: 7, total: 1, overdue: 1, blocked: 0, disclaimer: "Workflow only.", actions: [{ id: 11, project_id: 7, evidence_id: 4, impact_level: "high_attention", governing_rule: "evidence_removed", reason: "Evidence was removed.", action_text: "Confirm removal.", supporting_event_ids: ["evidence:4"], status: "open", priority: "urgent", due_at: "2026-07-15T00:00:00Z", owner_notes: null, resolution_notes: null, resolved_at: null, overdue: true, urgency_rank: 0, history: [] }] };

const response = (body: unknown, status = 200) => Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body });

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("ResearchFollowUpQueue", () => {
  it("renders deterministic urgency and traceability", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => String(input) === "/api/research-projects" ? response(projects) : response(queue)));
    render(<ResearchFollowUpQueue />);
    expect(await screen.findByText("Follow-up action tracker")).toBeInTheDocument();
    expect(await screen.findByText("OVERDUE")).toBeInTheDocument();
    expect(screen.getByText(/evidence 4/)).toBeInTheDocument();
    expect(screen.getByText(/evidence:4/)).toBeInTheDocument();
    expect(screen.getByText("Total")).toBeInTheDocument();
    expect(screen.getByText("Blocked")).toBeInTheDocument();
  });

  it("applies queue filters", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => String(input) === "/api/research-projects" ? response(projects) : response(queue));
    vi.stubGlobal("fetch", fetchMock);
    render(<ResearchFollowUpQueue />);
    await screen.findByText("Follow-up action tracker");
    fireEvent.change(screen.getByLabelText("Follow-up status filter"), { target: { value: "blocked" } });
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes("status=blocked"))).toBe(true));
  });

  it("surfaces queue failures", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => String(input) === "/api/research-projects" ? response(projects) : response({}, 500)));
    render(<ResearchFollowUpQueue />);
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be loaded");
  });
});
