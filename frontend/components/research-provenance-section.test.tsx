import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchProvenanceSection } from "@/components/research-provenance-section";

const projects = [{ id: 7, title: "Climate Review: 2026 / Draft", description: null, objective: "Validate claims", status: "active", context: {}, created_at: "2026-07-16T00:00:00Z", updated_at: "2026-07-16T00:00:00Z" }];
const ledger = { summary: { total_evidence: 0, total_events: 0, unresolved_contradictions: 0, superseded_claims: 0, missing_source_metadata: 0 }, entries: [], disclaimer: "History does not certify correctness." };
const packet = { schema_version: "1.0", generated_at: "2026-07-16T00:00:00Z", project: { id: 7, title: projects[0].title }, summary: ledger.summary, entries: [], disclaimer: ledger.disclaimer, integrity_sha256: "a".repeat(64) };

function response(body: unknown, status = 200) {
  return Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("ResearchProvenanceSection audit packet", () => {
  it("downloads formatted JSON with a safe filename", async () => {
    const click = vi.fn();
    vi.spyOn(document, "createElement").mockReturnValue({ href: "", download: "", click } as unknown as HTMLAnchorElement);
    const createObjectURL = vi.fn(() => "blob:audit");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/research-projects") return response(projects);
      if (url.includes("research-evidence-provenance")) return response(ledger);
      if (url.includes("research-evidence-audit-packet/7")) return response(packet);
      return response({}, 500);
    }));

    render(<ResearchProvenanceSection />);
    fireEvent.click(await screen.findByRole("button", { name: "Download audit packet" }));

    await waitFor(() => expect(click).toHaveBeenCalled());
    const anchor = vi.mocked(document.createElement).mock.results.at(-1)?.value as HTMLAnchorElement;
    expect(anchor.download).toBe("climate-review-2026-draft-evidence-audit-packet.json");
    expect(createObjectURL).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:audit");
  });

  it("surfaces packet generation failure", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/research-projects") return response(projects);
      if (url.includes("research-evidence-provenance")) return response(ledger);
      return response({}, 500);
    }));

    render(<ResearchProvenanceSection />);
    fireEvent.click(await screen.findByRole("button", { name: "Download audit packet" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be generated");
  });
});
