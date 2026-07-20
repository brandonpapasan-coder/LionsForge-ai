import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PersonalMemoryControlCenter } from "@/components/personal-memory-control-center";

const summary = {
  project_id: null,
  total_count: 2,
  active_count: 2,
  archived_count: 0,
  user_authored_count: 2,
  research_generated_count: 0,
  revision_count: 2,
  by_status: { provisional: 2 },
  by_category: { research_context: 2 },
  available_controls: ["inspect", "evidence_trace"],
};

const firstMemory = {
  id: 11,
  project_id: 7,
  statement: "Use primary evidence before commentary.",
  summary: "Prioritize primary evidence",
  category: "research_context",
  status: "provisional",
  confidence: 0.8,
  source_evidence_ids: [41, 99],
  revision_number: 1,
  revisions: [],
};

const secondMemory = {
  ...firstMemory,
  id: 12,
  summary: "Second record",
  statement: "Use a second record.",
  source_evidence_ids: [],
};

const unsupportedTrace = {
  memory_id: 11,
  requested_evidence_ids: [],
  evidence: [],
  unavailable_evidence_ids: [],
  health: {
    classification: "unsupported",
    total_count: 0,
    available_count: 0,
    unavailable_count: 0,
    approved_count: 0,
    needs_review_count: 0,
    supporting_count: 0,
    contradicting_count: 0,
    average_credibility: null,
    average_freshness: null,
    average_confidence: null,
    reasons: [],
    recommended_actions: [],
  },
};

function response(body: unknown, status = 200): Promise<Response> {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response);
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("PersonalMemoryControlCenter evidence trace", () => {
  it("shows evidence health, safe source links, and unavailable IDs", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/personal-memory/summary") return response(summary);
      if (url === "/api/personal-memory") return response([firstMemory, secondMemory]);
      if (url === "/api/personal-memory/11/evidence") {
        return response({
          memory_id: 11,
          requested_evidence_ids: [41, 99],
          unavailable_evidence_ids: [99],
          health: {
            classification: "adequate",
            total_count: 2,
            available_count: 1,
            unavailable_count: 1,
            approved_count: 1,
            needs_review_count: 0,
            supporting_count: 1,
            contradicting_count: 0,
            average_credibility: 0.95,
            average_freshness: 0.8,
            average_confidence: 0.9,
            reasons: ["The evidence is usable but still has quality or review gaps."],
            recommended_actions: ["Replace or restore unavailable evidence."],
          },
          evidence: [{
            id: 41,
            source_url: "https://example.com/source",
            source_title: "Primary study",
            publisher: "Example Institute",
            author: "A. Researcher",
            source_type: "primary",
            claim: "The intervention improved outcomes.",
            excerpt: "Measured outcomes improved during evaluation.",
            stance: "supports",
            validation_status: "approved",
            credibility_score: 0.95,
            freshness_score: 0.8,
            confidence_score: 0.9,
          }],
        });
      }
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<PersonalMemoryControlCenter />);
    const inventory = await screen.findByLabelText("Personal memory inventory");
    fireEvent.click(within(inventory).getByRole("button", { name: /Prioritize primary evidence/i }));
    fireEvent.click(screen.getByRole("button", { name: "View supporting evidence" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/personal-memory/11/evidence",
      expect.objectContaining({ cache: "no-store", signal: expect.any(AbortSignal) }),
    ));

    const panel = await screen.findByLabelText("Supporting evidence trace");
    const health = within(panel).getByLabelText("Evidence health assessment");
    expect(within(health).getByText("adequate")).toBeInTheDocument();
    expect(within(health).getByText(/1 of 2 linked items available/)).toBeInTheDocument();
    expect(within(health).getByText(/Average credibility 95%/)).toBeInTheDocument();
    expect(within(health).getByText("The evidence is usable but still has quality or review gaps.")).toBeInTheDocument();
    expect(within(health).getByText("Replace or restore unavailable evidence.")).toBeInTheDocument();

    expect(within(panel).getByLabelText("Evidence 41")).toBeInTheDocument();
    expect(within(panel).getByRole("link", { name: "Open source" })).toHaveAttribute(
      "href",
      "https://example.com/source",
    );
    expect(within(panel).getByText("Unavailable evidence IDs: 99.")).toBeInTheDocument();
  });

  it("shows unsupported health when no evidence is linked", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/personal-memory/summary") return response(summary);
      if (url === "/api/personal-memory") return response([secondMemory]);
      if (url === "/api/personal-memory/12/evidence") {
        return response({ ...unsupportedTrace, memory_id: 12 });
      }
      return response(null, 404);
    }));

    render(<PersonalMemoryControlCenter />);
    const inventory = await screen.findByLabelText("Personal memory inventory");
    fireEvent.click(within(inventory).getByRole("button", { name: /Second record/i }));
    fireEvent.click(screen.getByRole("button", { name: "View supporting evidence" }));

    const health = await screen.findByLabelText("Evidence health assessment");
    expect(within(health).getByText("unsupported")).toBeInTheDocument();
    expect(within(health).getByText(/Average credibility Unavailable/)).toBeInTheDocument();
    expect(screen.getByText("No supporting evidence is attached to this record.")).toBeInTheDocument();
  });

  it("aborts an active evidence request when the selected record changes", async () => {
    let evidenceSignal: AbortSignal | null | undefined;
    let resolveEvidence: ((value: Response) => void) | undefined;
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/personal-memory/summary") return response(summary);
      if (url === "/api/personal-memory") return response([firstMemory, secondMemory]);
      if (url === "/api/personal-memory/11/evidence") {
        evidenceSignal = init?.signal;
        return new Promise<Response>((resolve) => {
          resolveEvidence = resolve;
        });
      }
      return response(null, 404);
    }));

    render(<PersonalMemoryControlCenter />);
    const inventory = await screen.findByLabelText("Personal memory inventory");
    fireEvent.click(within(inventory).getByRole("button", { name: /Prioritize primary evidence/i }));
    fireEvent.click(screen.getByRole("button", { name: "View supporting evidence" }));
    await waitFor(() => expect(evidenceSignal).toBeDefined());

    fireEvent.click(within(inventory).getByRole("button", { name: /Second record/i }));
    expect(evidenceSignal?.aborted).toBe(true);

    resolveEvidence?.(await response(unsupportedTrace));
    await Promise.resolve();

    expect(screen.queryByLabelText("Supporting evidence trace")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View supporting evidence" })).toHaveAttribute("aria-expanded", "false");
  });

  it("aborts an active evidence request when the control center unmounts", async () => {
    let evidenceSignal: AbortSignal | null | undefined;
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/personal-memory/summary") return response(summary);
      if (url === "/api/personal-memory") return response([firstMemory]);
      if (url === "/api/personal-memory/11/evidence") {
        evidenceSignal = init?.signal;
        return new Promise<Response>(() => undefined);
      }
      return response(null, 404);
    }));

    const { unmount } = render(<PersonalMemoryControlCenter />);
    const inventory = await screen.findByLabelText("Personal memory inventory");
    fireEvent.click(within(inventory).getByRole("button", { name: /Prioritize primary evidence/i }));
    fireEvent.click(screen.getByRole("button", { name: "View supporting evidence" }));
    await waitFor(() => expect(evidenceSignal).toBeDefined());

    unmount();

    expect(evidenceSignal?.aborted).toBe(true);
  });

  it("resets the evidence panel when the selected record changes", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/personal-memory/summary") return response(summary);
      if (url === "/api/personal-memory") return response([firstMemory, secondMemory]);
      if (url === "/api/personal-memory/11/evidence") return response(unsupportedTrace);
      return response(null, 404);
    }));

    render(<PersonalMemoryControlCenter />);
    const inventory = await screen.findByLabelText("Personal memory inventory");
    fireEvent.click(within(inventory).getByRole("button", { name: /Prioritize primary evidence/i }));
    fireEvent.click(screen.getByRole("button", { name: "View supporting evidence" }));
    expect(await screen.findByLabelText("Supporting evidence trace")).toBeInTheDocument();

    fireEvent.click(within(inventory).getByRole("button", { name: /Second record/i }));
    expect(screen.queryByLabelText("Supporting evidence trace")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View supporting evidence" })).toHaveAttribute("aria-expanded", "false");
  });
});
