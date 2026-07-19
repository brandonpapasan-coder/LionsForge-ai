import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InvestigationWorkspace } from "@/components/investigation-workspace";

const investigation = {
  id: 7,
  title: "Validate a research claim",
  research_question: "Does the current evidence support the claim?",
  status: "open",
  created_at: "2026-07-19T12:00:00Z",
  updated_at: "2026-07-19T12:00:00Z",
};

describe("InvestigationWorkspace", () => {
  beforeEach(() => vi.unstubAllGlobals());

  it("renders private investigations and updates status", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/investigations" && !init?.method) {
        return new Response(JSON.stringify([investigation]), { status: 200 });
      }
      if (url === "/api/investigations/7/claims") {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url === "/api/investigations/7" && init?.method === "PATCH") {
        return new Response(JSON.stringify({ ...investigation, status: "in_review" }), { status: 200 });
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<InvestigationWorkspace />);
    expect(await screen.findByText("Validate a research claim")).toBeInTheDocument();
    expect(screen.getByText("Does the current evidence support the claim?")).toBeInTheDocument();

    const statusSelect = screen.getByLabelText("Validation status");
    fireEvent.change(statusSelect, { target: { value: "in_review" } });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/investigations/7", expect.objectContaining({ method: "PATCH" })));
    await waitFor(() => expect(statusSelect).toHaveValue("in_review"));
  });

  it("creates an investigation and supports the empty state", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/investigations" && init?.method === "POST") {
        return new Response(JSON.stringify(investigation), { status: 201 });
      }
      if (url === "/api/investigations") {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url === "/api/investigations/7/claims") {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response("{}", { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<InvestigationWorkspace />);
    expect(await screen.findByText("No investigations yet. Start with a research question above.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: investigation.title } });
    fireEvent.change(screen.getByLabelText("Research question"), { target: { value: investigation.research_question } });
    fireEvent.click(screen.getByRole("button", { name: "Create investigation" }));
    expect(await screen.findByText(investigation.title)).toBeInTheDocument();
  });

  it("keeps the page available when the workspace service fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 503 })));
    render(<InvestigationWorkspace />);
    expect(await screen.findByRole("alert")).toHaveTextContent("temporarily unavailable");
    expect(screen.getByRole("heading", { name: "Start an investigation" })).toBeInTheDocument();
  });
});