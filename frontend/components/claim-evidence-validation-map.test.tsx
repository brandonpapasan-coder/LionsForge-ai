import React from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ClaimEvidenceValidationMapPanel } from "@/components/claim-evidence-validation-map";
import type { ClaimEvidenceValidationMap } from "@/lib/investigations";

const activeMap: ClaimEvidenceValidationMap = {
  contract_version: "1.0",
  investigation_id: 7,
  title: "Source review",
  status: "active",
  summary_counts: { supported: 1, contested: 1, insufficient: 0, unreviewed: 0 },
  unresolved_gaps: ["Resolve the conflicting publication record."],
  generated_from: "stored_evidence_rules",
  generated_from_stored_state_at: "2026-07-25T16:00:00Z",
  interpretation_notice: "Statuses organize recorded evidence.",
  claims: [
    {
      claim_id: 1,
      sequence: 1,
      statement: "The record supports the stated timeline.",
      status: "supported",
      status_rule: "Supporting evidence exists and no contradiction is recorded.",
      relationship_counts: { supporting: 1, contradicting: 0, contextual: 0 },
      confidence_inputs: ["claim confidence: medium"],
      evidence_links: [{
        evidence_id: 10,
        source_title: "Primary record",
        source_url: "https://example.com/record",
        evidence_type: "primary",
        relationship: "supporting",
        stored_relationship: "supports",
        classification_rule: "Stored supports maps to supporting.",
        credibility_rating: "high",
        credibility_rationale: "Direct record.",
        notes: null,
      }],
      missing_evidence_requirements: [],
      unresolved_gaps: [],
      human_review: {
        status: "current",
        validation_status: "supported",
        confidence_level: "high",
        rationale: "The primary record directly supports the claim.",
        unresolved_questions: null,
        reviewed_at: "2026-07-25T16:00:00Z",
        authorship: "user_judgment",
      },
    },
    {
      claim_id: 2,
      sequence: 2,
      statement: "The publication date is uncontested.",
      status: "contested",
      status_rule: "At least one contradiction is recorded.",
      relationship_counts: { supporting: 1, contradicting: 1, contextual: 0 },
      confidence_inputs: [],
      evidence_links: [],
      missing_evidence_requirements: ["Add an independent dated source."],
      unresolved_gaps: ["Conflicting dates remain unresolved."],
      human_review: {
        status: "stale",
        validation_status: "mixed",
        confidence_level: "medium",
        rationale: "Earlier review predates the contradiction.",
        unresolved_questions: "Which date is authoritative?",
        reviewed_at: "2026-07-24T16:00:00Z",
        authorship: "user_judgment",
      },
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

describe("ClaimEvidenceValidationMapPanel", () => {
  it("renders supported and contested claims with evidence and human-review state", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response(activeMap)));
    render(<ClaimEvidenceValidationMapPanel investigationId={7} />);

    const supported = await screen.findByLabelText("The record supports the stated timeline.: supported");
    expect(within(supported).getByText(/Primary record/)).toBeInTheDocument();
    expect(within(supported).getByText(/Credibility input: high/)).toBeInTheDocument();

    const contested = screen.getByLabelText("The publication date is uncontested.: contested");
    expect(within(contested).getByText(/Human review: stale/)).toBeInTheDocument();
    expect(within(contested).getByText(/Add an independent dated source/)).toBeInTheDocument();
    expect(within(contested).getByText(/Conflicting dates remain unresolved/)).toBeInTheDocument();
  });

  it("renders the empty investigation state", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({ ...activeMap, status: "empty", claims: [] })));
    render(<ClaimEvidenceValidationMapPanel investigationId={7} />);
    expect(await screen.findByText(/No material claims are recorded/)).toBeInTheDocument();
  });

  it("retries after a temporary failure", async () => {
    const user = userEvent.setup();
    let calls = 0;
    vi.stubGlobal("fetch", vi.fn(() => {
      calls += 1;
      return calls === 1 ? response({ detail: "unavailable" }, 503) : response(activeMap);
    }));
    render(<ClaimEvidenceValidationMapPanel investigationId={7} />);
    await user.click(await screen.findByRole("button", { name: "Retry validation map" }));
    expect(await screen.findByLabelText("The record supports the stated timeline.: supported")).toBeInTheDocument();
    expect(calls).toBe(2);
  });
});
