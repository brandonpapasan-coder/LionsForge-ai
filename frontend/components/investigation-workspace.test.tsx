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

function investigationFetch(responseForPacket?: Response) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/investigations" && !init?.method) {
      return new Response(JSON.stringify([investigation]), { status: 200 });
    }
    if (url === "/api/investigations/7/claims") {
      return new Response(JSON.stringify([]), { status: 200 });
    }
    if (url === "/api/investigations/7/evidence-packet") {
      return responseForPacket ?? new Response("{}", { status: 404 });
    }
    if (url === "/api/investigations/7" && init?.method === "PATCH") {
      return new Response(JSON.stringify({ ...investigation, status: "in_review" }), { status: 200 });
    }
    return new Response("{}", { status: 404 });
  });
}

describe("InvestigationWorkspace", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("renders private investigations and updates status", async () => {
    const fetchMock = investigationFetch();
    vi.stubGlobal("fetch", fetchMock);

    render(<InvestigationWorkspace />);
    expect(await screen.findByText("Validate a research claim")).toBeInTheDocument();
    expect(screen.getByText("Does the current evidence support the claim?")).toBeInTheDocument();

    const statusSelect = screen.getByLabelText("Validation status");
    fireEvent.change(statusSelect, { target: { value: "in_review" } });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/investigations/7", expect.objectContaining({ method: "PATCH" })));
    await waitFor(() => expect(statusSelect).toHaveValue("in_review"));
  });

  it("downloads the exact evidence packet through the authenticated workspace proxy", async () => {
    const packet = { investigation: { id: 7 }, claims: [], interpretation_notice: "Human review required." };
    const fetchMock = investigationFetch(new Response(JSON.stringify(packet), {
      status: 200,
      headers: { "content-type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);
    const createObjectURL = vi.fn(() => "blob:evidence-packet");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
    let downloadedFilename = "";
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      downloadedFilename = this.download;
    });

    render(<InvestigationWorkspace />);
    fireEvent.click(await screen.findByRole("button", { name: "Download evidence packet" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/investigations/7/evidence-packet",
      { cache: "no-store" },
    ));
    await waitFor(() => expect(downloadedFilename).toBe("lionsforge-investigation-7-evidence-packet.json"));
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:evidence-packet");
  });

  it("reports a conservative error and does not download a failed export", async () => {
    const fetchMock = investigationFetch(new Response(JSON.stringify({ detail: "Not found" }), { status: 404 }));
    vi.stubGlobal("fetch", fetchMock);
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    render(<InvestigationWorkspace />);
    fireEvent.click(await screen.findByRole("button", { name: "Download evidence packet" }));

    expect(await screen.findByText(/No file was downloaded/)).toBeInTheDocument();
    expect(click).not.toHaveBeenCalled();
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
