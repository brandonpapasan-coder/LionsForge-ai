import React from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EvidenceGapRemediationPanel } from "@/components/evidence-gap-remediation-panel";
import type { EvidenceGapRemediationPlan } from "@/lib/investigations";

const activePlan: EvidenceGapRemediationPlan = {
  contract_version: "1.0",
  investigation_id: 7,
  title: "Source review",
  status: "action_required",
  action_counts: { resolve_contradiction: 1, collect_direct_evidence: 0, attach_initial_evidence: 0, refresh_human_review: 1 },
  generated_from: "validation_map_stored_inputs",
  generated_from_stored_state_at: "2026-07-25T16:00:00Z",
  interpretation_notice: "Actions are deterministic research prompts.",
  actions: [
    {
      claim_id: 1,
      claim_sequence: 1,
      statement: "The publication date is uncontested.",
      claim_status: "contested",
      priority: 1,
      priority_rule: "Contested claims are first because recorded contradiction must be resolved.",
      action_type: "resolve_contradiction",
      rationale: "Review and explicitly resolve the conflicting record.",
      source_requirements: [{
        requirement: "Resolve the recorded contradicting evidence.",
        source_constraints: ["Use a source with an identifiable title and URL."],
        derived_from: "recorded_gap",
      }],
      review_refresh_required: false,
      completion_criteria: ["Review every currently recorded contradicting evidence item."],
      stored_inputs: ["claim_status=contested", "contradicting_count=1"],
    },
    {
      claim_id: 2,
      claim_sequence: 2,
      statement: "The supported claim remains current.",
      claim_status: "supported",
      priority: 4,
      priority_rule: "Supported claims are included only when their human review is stale.",
      action_type: "refresh_human_review",
      rationale: "Refresh the judgment against current stored evidence.",
      source_requirements: [],
      review_refresh_required: true,
      completion_criteria: ["Record a new human validation judgment."],
      stored_inputs: ["claim_status=supported", "human_review_status=stale"],
    },
  ],
};

function response(body: unknown, status = 200) {
  return Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("EvidenceGapRemediationPanel", () => {
  it("renders priority, source constraints, completion criteria, and stale-review action", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response(activePlan)));
    render(<EvidenceGapRemediationPanel investigationId={7} />);

    const contested = await screen.findByLabelText("The publication date is uncontested.: priority 1");
    expect(within(contested).getByText(/Why this priority/)).toBeInTheDocument();
    expect(within(contested).getByText(/identifiable title and URL/)).toBeInTheDocument();
    expect(within(contested).getByText(/Review every currently recorded contradicting evidence item/)).toBeInTheDocument();

    const stale = screen.getByLabelText("The supported claim remains current.: priority 4");
    expect(within(stale).getByText(/Human review refresh:/)).toHaveTextContent("required");
    expect(within(stale).getByText(/No new source requirement is recorded/)).toBeInTheDocument();
  });

  it("renders complete and empty states", async () => {
    const fetchMock = vi.fn()
      .mockImplementationOnce(() => response({ ...activePlan, status: "complete", actions: [] }))
      .mockImplementationOnce(() => response({ ...activePlan, status: "empty", actions: [] }));
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<EvidenceGapRemediationPanel investigationId={7} />);
    expect(await screen.findByText(/No recorded evidence gap or stale review/)).toBeInTheDocument();
    unmount();

    render(<EvidenceGapRemediationPanel investigationId={8} />);
    expect(await screen.findByText(/No material claims are recorded/)).toBeInTheDocument();
  });

  it("retries after a temporary failure", async () => {
    const user = userEvent.setup();
    let calls = 0;
    vi.stubGlobal("fetch", vi.fn(() => {
      calls += 1;
      return calls === 1 ? response({ detail: "unavailable" }, 503) : response(activePlan);
    }));
    render(<EvidenceGapRemediationPanel investigationId={7} />);
    await user.click(await screen.findByRole("button", { name: "Retry remediation plan" }));
    expect(await screen.findByLabelText("The publication date is uncontested.: priority 1")).toBeInTheDocument();
    expect(calls).toBe(2);
  });
});