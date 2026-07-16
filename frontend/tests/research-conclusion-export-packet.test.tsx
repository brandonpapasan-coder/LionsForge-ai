import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchConclusionExportPacket } from "@/components/research-conclusion-export-packet";

const projects = [
  { id: 7, title: "Evidence Review", description: null, objective: "Review evidence", status: "active", context: {}, created_at: "2026-07-16T00:00:00Z", updated_at: "2026-07-16T00:00:00Z" },
  { id: 8, title: "Second Project", description: null, objective: "Second", status: "active", context: {}, created_at: "2026-07-16T00:00:00Z", updated_at: "2026-07-16T00:00:00Z" },
];
const packet = {
  content_sha256: "a".repeat(64), generated_at: "2026-07-16T00:00:00Z",
  content: {
    schema_version: "1.0", project_id: 7, project_title: "Evidence Review", conclusion_status: "finalized", conclusion_text: "Owner-authored conclusion.", evidence_ids: [4],
    evidence: [{ id: 4, source_title: "Primary source", claim: "A supported claim", validation_status: "approved" }],
    revisions: [{ revision_number: 1, status: "finalized", revision_note: "Owner finalized.", created_at: "2026-07-16T00:00:00Z" }],
    readiness: { state: "needs_review", blocking_count: 0, caution_count: 1, next_steps: ["Review evidence."], disclaimer: "Readiness is not truth certification." },
    disclaimer: "Export does not publish or certify a conclusion.",
  },
};
const response = (body: unknown, status = 200) => Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body });

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("ResearchConclusionExportPacket", () => {
  it("renders hash, readiness, evidence, and revisions", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => String(input) === "/api/research-projects" ? response(projects) : response(packet)));
    render(<ResearchConclusionExportPacket />);
    expect(await screen.findByText("Conclusion export packet")).toBeInTheDocument();
    expect(await screen.findByText(/Readiness: needs review/)).toBeInTheDocument();
    expect(screen.getByText(/Evidence 4: Primary source/)).toBeInTheDocument();
    expect(screen.getByText(/Revision 1 · finalized/)).toBeInTheDocument();
    expect(screen.getByText("a".repeat(64))).toBeInTheDocument();
  });

  it("switches projects and requests the selected packet", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => String(input) === "/api/research-projects" ? response(projects) : response(packet));
    vi.stubGlobal("fetch", fetchMock);
    render(<ResearchConclusionExportPacket />);
    const select = await screen.findByLabelText("Export packet project");
    fireEvent.change(select, { target: { value: "8" } });
    await waitFor(() => expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith("/8"))).toBe(true));
  });

  it("downloads the complete JSON packet with a deterministic name", async () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    const createObjectURL = vi.fn(() => "blob:packet");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { value: createObjectURL, configurable: true });
    Object.defineProperty(URL, "revokeObjectURL", { value: revokeObjectURL, configurable: true });
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => String(input) === "/api/research-projects" ? response(projects) : response(packet)));
    render(<ResearchConclusionExportPacket />);
    fireEvent.click(await screen.findByRole("button", { name: "Download JSON packet" }));
    expect(createObjectURL).toHaveBeenCalled();
    expect(click).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:packet");
  });

  it("surfaces packet failures", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => String(input) === "/api/research-projects" ? response(projects) : response({}, 500)));
    render(<ResearchConclusionExportPacket />);
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be loaded");
  });
});
