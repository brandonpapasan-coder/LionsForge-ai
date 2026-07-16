import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchConclusionWorkspace } from "@/components/research-conclusion-workspace";

const projects = [{ id: 7, title: "Evidence Review", description: null, objective: "Review evidence", status: "active", context: {}, created_at: "2026-07-16T00:00:00Z", updated_at: "2026-07-16T00:00:00Z" }];
const workspace = { project_id: 7, status: "draft", conclusion_text: "", evidence_ids: [], revision_count: 0, revisions: [], disclaimer: "Owner authored only." };
const readiness = { state: "needs_review", blocking_count: 0, caution_count: 1, next_steps: ["Review evidence."], disclaimer: "Readiness is not truth certification." };
const evidence = [{ id: 4, source_title: "Primary source", claim: "A supported claim", validation_status: "approved" }];
const response = (body: unknown, status = 200) => Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body });

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("ResearchConclusionWorkspace", () => {
  it("renders readiness warnings and selectable evidence", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/research-projects") return response(projects);
      if (url.includes("readiness")) return response(readiness);
      if (url.includes("evidence")) return response(evidence);
      return response(workspace);
    }));
    render(<ResearchConclusionWorkspace />);
    expect(await screen.findByText("User-authored conclusion")).toBeInTheDocument();
    expect(await screen.findByText(/Readiness: needs review/)).toBeInTheDocument();
    expect(screen.getByText(/Evidence 4: Primary source/)).toBeInTheDocument();
    expect(screen.getByText(/not truth certification/)).toBeInTheDocument();
  });

  it("saves selected evidence with owner-authored text", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/research-projects") return response(projects);
      if (url.includes("readiness")) return response(readiness);
      if (url.includes("evidence")) return response(evidence);
      if (init?.method === "PUT") return response({ ...workspace, conclusion_text: "My conclusion", evidence_ids: [4], revision_count: 1 });
      return response(workspace);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ResearchConclusionWorkspace />);
    const evidenceControl = await screen.findByText(/Evidence 4:/);
    fireEvent.change(screen.getByLabelText("Conclusion text"), { target: { value: "My conclusion" } });
    fireEvent.click(evidenceControl);
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PUT" && String(init.body).includes("My conclusion") && String(init.body).includes("4"))).toBe(true));
  });

  it("requires explicit confirmation before finalizing", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/research-projects") return response(projects);
      if (url.includes("readiness")) return response(readiness);
      if (url.includes("evidence")) return response(evidence);
      void init;
      return response(workspace);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ResearchConclusionWorkspace />);
    fireEvent.click(await screen.findByRole("button", { name: "Finalize conclusion" }));
    expect(confirm).toHaveBeenCalled();
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PUT")).toBe(false);
  });

  it("surfaces workspace failures", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => String(input) === "/api/research-projects" ? response(projects) : response({}, 500)));
    render(<ResearchConclusionWorkspace />);
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be loaded");
  });
});
