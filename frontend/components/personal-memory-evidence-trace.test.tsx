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

function response(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("PersonalMemoryControlCenter evidence trace", () => {
  it("loads evidence on request, shows safe source links, and reports missing IDs", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/personal-memory/summary") return response(summary);
      if (url === "/api/personal-memory") return response([firstMemory, secondMemory]);
      if (url === "/api/personal-memory/11/evidence") {
        return response({
          memory_id: 11,
          requested_evidence_ids: [41, 99],
          missing_evidence_ids: [99],
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

    expect(screen.queryByLabelText("Supporting evidence trace")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "View supporting evidence" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/personal-memory/11/evidence",
      { cache: "no-store" },
    ));
    const panel = await screen.findByLabelText("Supporting evidence trace");
    expect(within(panel).getByLabelText("Evidence 41")).toBeInTheDocument();
    expect(within(panel).getByRole("link", { name: "Open source" })).toHaveAttribute(
      "href",
      "https://example.com/source",
    );
    expect(within(panel).getByText("Unavailable evidence IDs: 99.")).toBeInTheDocument();
  });

  it("resets the evidence panel when the selected record changes", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/personal-memory/summary") return response(summary);
      if (url === "/api/personal-memory") return response([firstMemory, secondMemory]);
      if (url === "/api/personal-memory/11/evidence") {
        return response({ memory_id: 11, requested_evidence_ids: [], evidence: [], missing_evidence_ids: [] });
      }
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
