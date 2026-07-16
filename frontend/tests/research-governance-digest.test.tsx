import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchGovernanceDigest } from "@/components/research-governance-digest";

const projects = [{ id: 7, title: "Climate Review", description: null, objective: "Validate claims", status: "active", context: {}, created_at: "2026-07-16T00:00:00Z", updated_at: "2026-07-16T00:00:00Z" }];
const preference = { id: 1, project_ids: [7], impact_levels: ["high_attention", "review_required", "informational"], window_days: 30, cadence: "weekly", created_at: "2026-07-16T00:00:00Z", updated_at: "2026-07-16T00:00:00Z" };
const digest = { generated_at: "2026-07-16T12:00:00Z", window_start: "2026-06-16T12:00:00Z", window_end: "2026-07-16T12:00:00Z", summary: { newly_opened: 1, overdue: 1, reopened: 0, deferred: 0, recently_resolved: 0, total_items: 2 }, items: [{ category: "overdue", action_id: 11, project_id: 7, evidence_id: 4, impact_level: "high_attention", governing_rule: "evidence_removed", status: "open", reason: "Evidence was removed.", action_text: "Confirm removal.", supporting_event_ids: ["evidence:4"], age_days: 10, reopen_count: 0 }], content_sha256: "a".repeat(64), disclaimer: "Workflow only." };

function response(body: unknown, status = 200) { return Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body }); }

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("ResearchGovernanceDigest", () => {
  it("loads preferences and renders a traceable preview", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/research-projects") return response(projects);
      if (url.endsWith("/preferences")) return response(preference);
      if (url.endsWith("/history")) return response({ snapshots: [] });
      if (url.includes("/preview?")) return response(digest);
      return response({}, 500);
    }));
    render(<ResearchGovernanceDigest />);
    expect(await screen.findByText("Governance review digest")).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Preview digest" }));
    expect(await screen.findByText("Governance items requiring context")).toBeInTheDocument();
    expect(screen.getByText("OVERDUE")).toBeInTheDocument();
    expect(screen.getByText((_, element) => element?.tagName === "P" && element.textContent?.includes("Evidence: 4") === true)).toBeInTheDocument();
    expect(screen.getByText(/evidence:4/)).toBeInTheDocument();
  });

  it("surfaces preference loading failures", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      if (String(input) === "/api/research-projects") return response(projects);
      return response({}, 500);
    }));
    render(<ResearchGovernanceDigest />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("could not be loaded"));
  });
});
