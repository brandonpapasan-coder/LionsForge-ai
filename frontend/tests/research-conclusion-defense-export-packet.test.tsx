import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchConclusionDefenseExportPacket } from "@/components/research-conclusion-defense-export-packet";

const projects = [
  { id: 7, title: "Evidence Review", description: null, objective: "Review evidence", status: "active", context: {}, created_at: "2026-07-16T00:00:00Z", updated_at: "2026-07-16T00:00:00Z" },
  { id: 8, title: "Second Project", description: null, objective: "Second", status: "active", context: {}, created_at: "2026-07-16T00:00:00Z", updated_at: "2026-07-16T00:00:00Z" },
];
const packet = {
  content_sha256: "b".repeat(64), generated_at: "2026-07-16T00:00:00Z",
  content: {
    schema_version: "1.0",
    conclusion: { project_id: 7, project_title: "Evidence Review", conclusion_status: "finalized", conclusion_text: "Owner conclusion.", evidence: [{ id: 4 }], revisions: [{ revision_number: 1 }], readiness: { state: "needs_review" } },
    defense: { status: "complete", conclusion_revision_number: 1, evidence_coverage: "Coverage", strongest_counterargument: "Counterargument", known_limitations: "Limitations", unresolved_questions: "Questions", confidence_rationale: "Rationale", missing_sections: [], revisions: [{ revision_number: 1, status: "complete", revision_note: "Initial defense", created_at: "2026-07-16T00:00:00Z" }] },
    disclaimer: "Export does not certify the work.",
  },
};
const response = (body: unknown, status = 200) => Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body });

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("ResearchConclusionDefenseExportPacket", () => {
  it("renders conclusion, defense, hash, and revision trail", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => String(input) === "/api/research-projects" ? response(projects) : response(packet)));
    render(<ResearchConclusionDefenseExportPacket />);
    expect(await screen.findByText("Conclusion defense export packet")).toBeInTheDocument();
    expect(await screen.findByText("Defense: complete")).toBeInTheDocument();
    expect(screen.getByText("Owner conclusion.")).toBeInTheDocument();
    expect(screen.getByText(/Revision 1 · complete/)).toBeInTheDocument();
    expect(screen.getByText("b".repeat(64))).toBeInTheDocument();
  });

  it("switches projects and requests the selected packet", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => String(input) === "/api/research-projects" ? response(projects) : response(packet));
    vi.stubGlobal("fetch", fetchMock);
    render(<ResearchConclusionDefenseExportPacket />);
    fireEvent.change(await screen.findByLabelText("Conclusion defense export project"), { target: { value: "8" } });
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith("/8"))).toBe(true));
  });

  it("downloads the combined JSON packet", async () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    Object.defineProperty(URL, "createObjectURL", { value: vi.fn(() => "blob:packet"), configurable: true });
    Object.defineProperty(URL, "revokeObjectURL", { value: vi.fn(), configurable: true });
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => String(input) === "/api/research-projects" ? response(projects) : response(packet)));
    render(<ResearchConclusionDefenseExportPacket />);
    fireEvent.click(await screen.findByRole("button", { name: "Download combined JSON packet" }));
    expect(click).toHaveBeenCalled();
  });

  it("surfaces packet failures", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => String(input) === "/api/research-projects" ? response(projects) : response({}, 500)));
    render(<ResearchConclusionDefenseExportPacket />);
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be loaded");
  });
});
