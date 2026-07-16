import React from "react";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchProvenancePanel } from "@/components/research-provenance-panel";

function response(body: unknown, status = 200) {
  return Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body });
}

const ledger = {
  summary: { total_evidence: 2, total_events: 2, unresolved_contradictions: 1, superseded_claims: 1, missing_source_metadata: 1 },
  entries: [
    {
      event_id: "evidence:1",
      event_type: "evidence_created",
      evidence_id: 1,
      project_id: 4,
      source_title: "Field observation",
      source_type: "primary",
      claim: "The first observation supported the working hypothesis.",
      validation_status: "needs_review",
      contradiction_key: "observation-pattern",
      supersedes_evidence_id: null,
      reviewer_notes: null,
      warning: "Source URL is missing.",
      occurred_at: "2026-07-16T10:00:00Z",
    },
    {
      event_id: "supersession:2",
      event_type: "claim_superseded",
      evidence_id: 2,
      project_id: 4,
      source_title: "Revised observation",
      source_type: "secondary",
      claim: "The revised observation narrowed the original hypothesis.",
      validation_status: "unverified",
      contradiction_key: "observation-pattern",
      supersedes_evidence_id: 1,
      reviewer_notes: null,
      warning: null,
      occurred_at: "2026-07-16T11:00:00Z",
    },
  ],
  disclaimer: "Provenance traces origin and revision history; it does not certify truth or accuracy.",
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("ResearchProvenancePanel", () => {
  it("renders summary, warnings, contradictions, and supersession", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response(ledger)));
    render(<ResearchProvenancePanel projectId={4} />);

    expect(await screen.findByText("Field observation")).toBeInTheDocument();
    expect(screen.getByText("Source URL is missing.")).toBeInTheDocument();
    expect(screen.getByText("Supersedes evidence:")).toBeInTheDocument();
    expect(screen.getByText("does not certify truth", { exact: false })).toBeInTheDocument();
  });

  it("renders an actionable empty state", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({ ...ledger, entries: [], summary: { ...ledger.summary, total_evidence: 0, total_events: 0 } })));
    render(<ResearchProvenancePanel projectId={4} />);

    expect(await screen.findByText("No provenance entries yet.")).toBeInTheDocument();
  });

  it("surfaces request failures", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({}, 503)));
    render(<ResearchProvenancePanel projectId={4} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("could not be loaded");
  });
});
