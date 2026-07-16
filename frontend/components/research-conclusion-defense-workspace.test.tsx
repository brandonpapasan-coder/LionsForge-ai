import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ResearchConclusionDefenseWorkspace } from "./research-conclusion-defense-workspace";

const projects = [{ id: 1, title: "Defense project" }, { id: 2, title: "Second project" }];
const emptyDefense = {
  project_id: 1,
  conclusion_revision_number: null,
  evidence_ids: [],
  evidence_coverage: "",
  strongest_counterargument: "",
  known_limitations: "",
  unresolved_questions: "",
  confidence_rationale: "",
  status: "incomplete",
  missing_sections: ["evidence_coverage", "strongest_counterargument", "known_limitations", "unresolved_questions", "confidence_rationale"],
  revision_count: 0,
  revisions: [],
  disclaimer: "Completeness only means all reflection sections were supplied.",
};
const conclusion = { revisions: [{ revision_number: 1, status: "finalized", created_at: "2026-07-16T12:00:00Z" }] };
const evidence = [{ id: 9, source_title: "Primary source", claim: "Supported claim", validation_status: "reviewed" }];

function response(body: unknown, ok = true) {
  return Promise.resolve({ ok, status: ok ? 200 : 500, json: async () => body } as Response);
}

function installFetch(defenseBody = emptyDefense) {
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/research-projects") return response(projects);
    if (url.includes("research-conclusion-workspace")) return response(conclusion);
    if (url.includes("research-conclusion-evidence")) return response(evidence);
    if (url.includes("research-conclusion-defense") && init?.method === "PUT") {
      return response({ ...defenseBody, status: "complete", missing_sections: [], revision_count: 1, revisions: [{ id: 1, revision_number: 1, status: "complete", missing_sections: [], revision_note: "Completed", created_at: "2026-07-16T12:30:00Z" }] });
    }
    if (url.includes("research-conclusion-defense")) return response(defenseBody);
    return response({}, false);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("ResearchConclusionDefenseWorkspace", () => {
  beforeEach(() => { vi.restoreAllMocks(); });

  it("renders missing sections and linked research controls", async () => {
    installFetch();
    render(<ResearchConclusionDefenseWorkspace />);
    expect(await screen.findByText("Completeness: incomplete")).toBeInTheDocument();
    expect(screen.getByText(/Evidence coverage, Strongest counterargument/)).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Revision 1 · finalized" })).toBeInTheDocument();
    expect(screen.getByText(/Evidence 9: Primary source/)).toBeInTheDocument();
  });

  it("saves user-authored reflections with selected links", async () => {
    const fetchMock = installFetch();
    render(<ResearchConclusionDefenseWorkspace />);
    await screen.findByText("Completeness: incomplete");
    fireEvent.change(screen.getByLabelText("Conclusion revision"), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("checkbox"));
    for (const label of ["Evidence coverage", "Strongest counterargument", "Known limitations", "Unresolved questions", "Confidence rationale"]) {
      fireEvent.change(screen.getByLabelText(label), { target: { value: `${label} response` } });
    }
    fireEvent.change(screen.getByLabelText("Defense revision note"), { target: { value: "Completed" } });
    fireEvent.click(screen.getByRole("button", { name: "Save defense review" }));
    await screen.findByText("Completeness: complete");
    const putCall = fetchMock.mock.calls.find((call) => call[1]?.method === "PUT");
    expect(putCall).toBeDefined();
    const payload = JSON.parse(String(putCall?.[1]?.body));
    expect(payload.conclusion_revision_number).toBe(1);
    expect(payload.evidence_ids).toEqual([9]);
    expect(payload.confidence_rationale).toBe("Confidence rationale response");
    expect(screen.getByText(/Revision 1 · complete/)).toBeInTheDocument();
  });

  it("reloads when the project changes", async () => {
    const fetchMock = installFetch();
    render(<ResearchConclusionDefenseWorkspace />);
    await screen.findByText("Completeness: incomplete");
    fireEvent.change(screen.getByLabelText("Defense project"), { target: { value: "2" } });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/research-conclusion-defense/2", { cache: "no-store" }));
  });

  it("shows a save error", async () => {
    installFetch();
    const original = global.fetch;
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === "PUT") return response({}, false);
      return original(input, init);
    }));
    render(<ResearchConclusionDefenseWorkspace />);
    await screen.findByText("Completeness: incomplete");
    fireEvent.click(screen.getByRole("button", { name: "Save defense review" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The defense review could not be saved.");
  });
});
