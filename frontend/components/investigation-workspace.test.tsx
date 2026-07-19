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
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([investigation]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...investigation, status: "in_review" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    render(<InvestigationWorkspace />);
    expect(await screen.findByText("Validate a research claim")).toBeInTheDocument();
    expect(screen.getByText("Does the current evidence support the claim?")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Validation status"), { target: { value: "in_review" } });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/investigations/7", expect.objectContaining({ method: "PATCH" })));
    expect(await screen.findByDisplayValue("in review")).toBeInTheDocument();
  });

  it("creates an investigation and supports the empty state", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify([]), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(investigation), { status: 201 }));
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
