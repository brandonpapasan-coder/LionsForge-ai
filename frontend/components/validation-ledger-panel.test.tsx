import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ValidationLedgerPanel } from "@/components/validation-ledger-panel";

const claim = {
  id: 11,
  investigation_id: 4,
  statement: "The evidence supports the conclusion.",
  confidence_level: "medium",
  confidence_rationale: "Mixed evidence remains.",
  created_at: "2026-07-19T12:00:00Z",
  updated_at: "2026-07-19T12:00:00Z",
};

const judgment = {
  id: 31,
  claim_id: 11,
  reviewer_id: 7,
  validation_status: "inconclusive",
  confidence_level: "medium",
  rationale: "The record is incomplete.",
  unresolved_questions: "Was the dataset independently replicated?",
  reviewed_at: "2026-07-19T13:00:00Z",
  is_stale: false,
};

describe("ValidationLedgerPanel", () => {
  beforeEach(() => vi.unstubAllGlobals());

  it("records an immutable judgment and displays it", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([claim]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(judgment), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);

    render(<ValidationLedgerPanel investigationId={4} />);
    expect(await screen.findByText(claim.statement)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Review rationale"), { target: { value: judgment.rationale } });
    fireEvent.change(screen.getByLabelText("Unresolved questions"), { target: { value: judgment.unresolved_questions } });
    fireEvent.click(screen.getByRole("button", { name: "Record immutable judgment" }));

    expect(await screen.findByText(judgment.rationale)).toBeInTheDocument();
    expect(screen.getByText(`Unresolved: ${judgment.unresolved_questions}`)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/investigations/claims/11/judgments",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("loads history and flags stale judgments", async () => {
    const stale = { ...judgment, id: 32, is_stale: true };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([claim]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify([stale, judgment]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    render(<ValidationLedgerPanel investigationId={4} />);
    expect(await screen.findByText(claim.statement)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show validation history" }));

    expect(await screen.findByText("Stale judgment: the claim or evidence changed after this review.")).toBeInTheDocument();
    expect(screen.getAllByText(judgment.rationale)).toHaveLength(2);
  });

  it("keeps the workspace usable when history is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 503 })));
    render(<ValidationLedgerPanel investigationId={4} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("temporarily unavailable");
    expect(screen.getByText("Validation ledger")).toBeInTheDocument();
  });
});
