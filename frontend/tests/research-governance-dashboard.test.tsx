import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchGovernanceDashboard } from "@/components/research-governance-dashboard";

const dashboard = {
  project_id: 7,
  total_actions: 2,
  status_metrics: [{ key: "open", label: "Open", count: 1, action_ids: [11] }],
  impact_metrics: [{ key: "high_attention", label: "High Attention", count: 1, action_ids: [11] }],
  rule_metrics: [{ key: "evidence_removed", label: "Evidence Removed", count: 1, action_ids: [11] }],
  aging_metrics: [{ key: "8_30_days", label: "8 30 Days", count: 1, action_ids: [11] }],
  overdue_count: 1,
  repeatedly_reopened_count: 1,
  throughput: { resolved_transitions: 2, reopened_transitions: 1, net_resolved: 1, window_days: 30, action_ids: [11] },
  trace_items: [{ action_id: 11, evidence_id: 4, impact_level: "high_attention", governing_rule: "evidence_removed", status: "open", reason: "Evidence was removed.", action_text: "Confirm removal.", supporting_event_ids: ["evidence:4"], age_days: 10, age_bucket: "8_30_days", overdue: true, reopen_count: 2 }],
  disclaimer: "Workflow metrics only.",
};

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("ResearchGovernanceDashboard", () => {
  it("renders metrics and traceable overdue actions", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: true, status: 200, json: async () => dashboard })));
    render(<ResearchGovernanceDashboard projectId={7} />);
    expect(await screen.findByText("Review dashboard")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Total actions")).toBeInTheDocument());
    expect(screen.getByText("OVERDUE")).toBeInTheDocument();
    expect(screen.getByText(/Action 11 · evidence 4/)).toBeInTheDocument();
    expect(screen.getByText(/evidence:4/)).toBeInTheDocument();
  });

  it("surfaces dashboard failures", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: false, status: 500, json: async () => ({}) })));
    render(<ResearchGovernanceDashboard projectId={7} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be loaded");
  });
});
