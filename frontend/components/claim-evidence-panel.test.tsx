import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ClaimEvidencePanel } from "@/components/claim-evidence-panel";

const claim = {
  id: 11,
  investigation_id: 4,
  statement: "The evidence supports the conclusion.",
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
    expect(await screen.findByText(evidence.source_title)).toBeInTheDocument();
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
    expect(await screen.findByText(evidence.source_title)).toBeInTheDocument();
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
