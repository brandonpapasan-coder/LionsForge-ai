import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { InvestigationProvenanceTimelinePanel } from "@/components/investigation-provenance-timeline";

function response(body: unknown, status = 200) {
  return Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body });
}

const timeline = {
  contract_version: "1.0",
  investigation_id: 7,
  title: "Provenance",
  status: "active",
  generated_from: "stored_investigation_records",
  interpretation_notice: "Chronology only.",
  events: [
    { event_key: "remediation_progress_history:4:recorded", category: "remediation_history", action: "recorded", entity_type: "remediation_progress_history", entity_id: 4, claim_id: 1, claim_statement: "The claim", authorship: "user_authored", summary: "Append-only remediation history recorded with status blocked.", occurred_at: "2026-07-25T18:00:00Z", source_table: "remediation_progress_history", source_record_id: 4 },
    { event_key: "claim_validation_judgments:3:reviewed", category: "validation", action: "reviewed", entity_type: "claim_validation_judgment", entity_id: 3, claim_id: 1, claim_statement: "The claim", authorship: "human_judgment", summary: "Human validation judgment recorded: mixed; confidence medium.", occurred_at: "2026-07-25T17:00:00Z", source_table: "claim_validation_judgments", source_record_id: 3 },
    { event_key: "claim_evidence:2:created", category: "evidence", action: "created", entity_type: "claim_evidence", entity_id: 2, claim_id: 1, claim_statement: "The claim", authorship: "user_authored", summary: "Evidence attached: Primary source (supports).", occurred_at: "2026-07-25T16:00:00Z", source_table: "claim_evidence", source_record_id: 2 },
  ],
};

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("InvestigationProvenanceTimelinePanel", () => {
  it("renders provenance and filters by category", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn(() => response(timeline)));
    render(<InvestigationProvenanceTimelinePanel investigationId={7} />);

    expect(await screen.findByText(/Append-only remediation history/)).toBeInTheDocument();
    expect(screen.getByText(/not validation evidence/)).toBeInTheDocument();
    expect(screen.getByText(/claim_validation_judgments record 3/)).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Activity category"), "evidence");
    expect(screen.getByText(/Evidence attached/)).toBeInTheDocument();
    expect(screen.queryByText(/Human validation judgment/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Append-only remediation history/)).not.toBeInTheDocument();
  });

  it("renders empty state", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({ ...timeline, status: "empty", events: [] })));
    render(<InvestigationProvenanceTimelinePanel investigationId={7} />);
    expect(await screen.findByText(/No stored claim, evidence, judgment, or remediation activity/)).toBeInTheDocument();
  });

  it("renders failure and retry states", async () => {
    const user = userEvent.setup();
    let calls = 0;
    vi.stubGlobal("fetch", vi.fn(() => {
      calls += 1;
      return calls === 1 ? response({}, 503) : response({ ...timeline, status: "empty", events: [] });
    }));
    render(<InvestigationProvenanceTimelinePanel investigationId={7} />);
    await user.click(await screen.findByRole("button", { name: "Retry provenance timeline" }));
    expect(await screen.findByText(/No stored claim, evidence, judgment, or remediation activity/)).toBeInTheDocument();
  });
});
