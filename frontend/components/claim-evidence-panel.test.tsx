import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ClaimEvidencePanel } from "@/components/claim-evidence-panel";

const claim = {
  id: 11,
  investigation_id: 4,
  statement: "The evidence supports the conclusion.",
  confidence_level: null,
  confidence_rationale: null,
  created_at: "2026-07-19T12:00:00Z",
  updated_at: "2026-07-19T12:00:00Z",
};

const evidence = {
  id: 21,
  claim_id: 11,
  source_title: "Primary source",
  source_url: "https://example.com/source",
  evidence_type: "primary",
  relationship: "supports",
  notes: "Direct observation",
  credibility_rating: null,
  credibility_rationale: null,
  created_at: "2026-07-19T12:00:00Z",
  updated_at: "2026-07-19T12:00:00Z",
};

describe("ClaimEvidencePanel", () => {
  beforeEach(() => vi.unstubAllGlobals());

  it("creates a claim and attaches evidence", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(claim), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(evidence), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);

    render(<ClaimEvidencePanel investigationId={4} />);
    expect(await screen.findByText("No claims mapped yet.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Claim statement"), { target: { value: claim.statement } });
    fireEvent.click(screen.getByRole("button", { name: "Add claim" }));
    expect(await screen.findByText(claim.statement)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Source title"), { target: { value: evidence.source_title } });
    fireEvent.change(screen.getByLabelText("Source URL"), { target: { value: evidence.source_url } });
    fireEvent.click(screen.getByRole("button", { name: "Attach evidence" }));
    expect(await screen.findByRole("link", { name: evidence.source_title })).toHaveAttribute("href", evidence.source_url);
  });

  it("records assessments and shows transparent summaries", async () => {
    const assessedClaim = { ...claim, confidence_level: "medium", confidence_rationale: "Mixed evidence remains." };
    const assessedEvidence = { ...evidence, credibility_rating: "high", credibility_rationale: "Direct primary record." };
    const claimSummary = {
      claim_id: 11,
      confidence_level: "medium",
      supporting_count: 1,
      contradicting_count: 1,
      neutral_count: 0,
      assessed_evidence_count: 1,
      total_evidence_count: 2,
      has_unresolved_contradiction: true,
    };
    const investigationSummary = {
      investigation_id: 4,
      claim_count: 1,
      assessed_claim_count: 1,
      low_confidence_count: 0,
      medium_confidence_count: 1,
      high_confidence_count: 0,
      unresolved_contradiction_count: 1,
      claims: [claimSummary],
    };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([claim]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([evidence]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(assessedClaim), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(claimSummary), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(assessedEvidence), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(claimSummary), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(investigationSummary), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    render(<ClaimEvidencePanel investigationId={4} />);
    expect(await screen.findByText(claim.statement)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show evidence" }));
    expect(await screen.findByText(evidence.source_title)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Confidence level"), { target: { value: "medium" } });
    fireEvent.change(screen.getByLabelText("Confidence rationale"), { target: { value: "Mixed evidence remains." } });
    fireEvent.click(screen.getByRole("button", { name: "Save claim assessment" }));
    expect(await screen.findByText("Mixed evidence remains.", { selector: "p" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Credibility rating"), { target: { value: "high" } });
    fireEvent.change(screen.getByLabelText("Credibility rationale"), { target: { value: "Direct primary record." } });
    fireEvent.click(screen.getByRole("button", { name: "Save evidence assessment" }));
    expect(await screen.findByText("Direct primary record.", { selector: "p" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Show validation summary" }));
    expect(await screen.findByText("1 claims contain unresolved contradictory evidence.")).toBeInTheDocument();
    expect(screen.getByText("Assessments are user-entered judgments, not automated declarations of truth.")).toBeInTheDocument();
  });

  it("loads and deletes owner-scoped claim data", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([claim]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([evidence]), { status: 200 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    render(<ClaimEvidencePanel investigationId={4} />);
    expect(await screen.findByText(claim.statement)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show evidence" }));
    expect(await screen.findByRole("link", { name: evidence.source_title })).toHaveAttribute("href", evidence.source_url);
    fireEvent.click(screen.getByRole("button", { name: "Delete claim" }));
    await waitFor(() => expect(screen.queryByText(claim.statement)).not.toBeInTheDocument());
  });

  it("keeps the panel available when claims fail to load", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 503 })));
    render(<ClaimEvidencePanel investigationId={4} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("temporarily unavailable");
    expect(screen.getByLabelText("Claim statement")).toBeInTheDocument();
  });
});
