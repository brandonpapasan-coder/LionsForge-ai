import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchProvenanceSection } from "@/components/research-provenance-section";

const projects = [{ id: 7, title: "Review project", description: null, objective: "Validate claims", status: "active", context: {}, created_at: "2026-07-16T00:00:00Z", updated_at: "2026-07-16T00:00:00Z" }];
const ledger = { summary: { total_evidence: 0, total_events: 0, unresolved_contradictions: 0, superseded_claims: 0, missing_source_metadata: 0 }, entries: [], disclaimer: "History only." };
const action = { id: 11, project_id: 7, evidence_id: 3, action_key: "a".repeat(64), impact_level: "high_attention", governing_rule: "evidence_removed", reason: "Evidence was removed.", action_text: "Confirm the removal rationale.", supporting_event_ids: ["evidence:3"], status: "open", history: [] };
const plan = { project_id: 7, generated: 0, existing: 1, actions: [action], disclaimer: "Review actions do not modify claims." };

function response(body: unknown, status = 200) { return Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body }); }

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("Research review action queue", () => {
  it("loads persisted actions and records a confirmed state transition", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.spyOn(window, "prompt").mockReturnValue("Reviewed by owner.");
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/research-projects") return response(projects);
      if (url.includes("research-evidence-provenance")) return response(ledger);
      if (url.includes("research-evidence-review-actions/projects/7")) return response(plan);
      if (url.endsWith("research-evidence-review-actions/11") && init?.method === "PATCH") return response({ ...action, status: "acknowledged", history: [{ id: 1, previous_status: "open", new_status: "acknowledged", note: "Reviewed by owner.", created_at: "2026-07-16T00:01:00Z" }] });
      return response({}, 500);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ResearchProvenanceSection />);
    expect(await screen.findByText("Confirm the removal rationale.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Acknowledge" }));
    await waitFor(() => expect(screen.getByText("ACKNOWLEDGED")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith("/api/research-evidence-review-actions/11", expect.objectContaining({ method: "PATCH" }));
    expect(screen.getByText(/open → acknowledged/)).toBeInTheDocument();
  });

  it("filters the queue by impact and completion state", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/research-projects") return response(projects);
      if (url.includes("research-evidence-provenance")) return response(ledger);
      if (url.includes("research-evidence-review-actions/projects/7")) return response({ ...plan, actions: [action, { ...action, id: 12, impact_level: "informational", status: "resolved", action_text: "Read the new review note." }] });
      return response({}, 500);
    }));
    render(<ResearchProvenanceSection />);
    await screen.findByText("Confirm the removal rationale.");
    fireEvent.change(screen.getByLabelText("Review action filter"), { target: { value: "resolved" } });
    expect(screen.getByText("Read the new review note.")).toBeInTheDocument();
    expect(screen.queryByText("Confirm the removal rationale.")).not.toBeInTheDocument();
  });
});
