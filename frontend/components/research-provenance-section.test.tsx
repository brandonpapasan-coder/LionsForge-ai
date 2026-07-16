import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchProvenanceSection } from "@/components/research-provenance-section";

const projects = [{ id: 7, title: "Climate Review: 2026 / Draft", description: null, objective: "Validate claims", status: "active", context: {}, created_at: "2026-07-16T00:00:00Z", updated_at: "2026-07-16T00:00:00Z" }];
const ledger = { summary: { total_evidence: 0, total_events: 0, unresolved_contradictions: 0, superseded_claims: 0, missing_source_metadata: 0 }, entries: [], disclaimer: "History does not certify correctness." };
const packet = { schema_version: "1.0", generated_at: "2026-07-16T00:00:00Z", project: { id: 7, title: projects[0].title }, summary: ledger.summary, entries: [], disclaimer: ledger.disclaimer, content_sha256: "a".repeat(64) };
const verification = {
  valid: true,
  schema_version_supported: true,
  integrity_matches: true,
  chronology_valid: true,
  supersession_references_valid: true,
  computed_sha256: "b".repeat(64),
  checks: [
    { code: "schema_version", passed: true, message: "Schema version is supported." },
    { code: "integrity_sha256", passed: true, message: "Integrity digest matches the canonical packet content." },
  ],
  disclaimer: "Packet verification confirms consistency only and does not certify claim truth.",
};

function response(body: unknown, status = 200) {
  return Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body });
}

function jsonFile(body: unknown, name = "packet.json") {
  return new File([JSON.stringify(body)], name, { type: "application/json" });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("ResearchProvenanceSection audit packet", () => {
  it("downloads formatted JSON with a safe filename", async () => {
    const originalCreateElement = document.createElement.bind(document);
    const click = vi.fn();
    const downloadAnchor = originalCreateElement("a") as HTMLAnchorElement;
    vi.spyOn(downloadAnchor, "click").mockImplementation(click);
    vi.spyOn(document, "createElement").mockImplementation(((tagName: string, options?: ElementCreationOptions) => {
      if (tagName.toLowerCase() === "a") return downloadAnchor;
      return originalCreateElement(tagName, options);
    }) as typeof document.createElement);
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
    expect(downloadAnchor.download).toBe("climate-review-2026-draft-evidence-audit-packet.json");
    expect(createObjectURL).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:audit");
  });

  it("shows passing verification checks for a valid packet", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/research-projects") return response(projects);
      if (url.includes("research-evidence-provenance")) return response(ledger);
      if (url.endsWith("/verify")) return response(verification);
      return response({}, 500);
    }));

    render(<ResearchProvenanceSection />);
    const input = await screen.findByLabelText("Verify audit packet");
    fireEvent.change(input, { target: { files: [jsonFile(packet)] } });

    expect(await screen.findByText("Packet passed verification")).toBeInTheDocument();
    expect(screen.getByText("integrity sha256")).toBeInTheDocument();
    expect(screen.getAllByText("PASS")).toHaveLength(2);
  });

  it("shows failed checks when packet integrity does not match", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/research-projects") return response(projects);
      if (url.includes("research-evidence-provenance")) return response(ledger);
      if (url.endsWith("/verify")) return response({
        ...verification,
        valid: false,
        integrity_matches: false,
        checks: [{ code: "integrity_sha256", passed: false, message: "Integrity digest does not match." }],
      });
      return response({}, 500);
    }));

    render(<ResearchProvenanceSection />);
    fireEvent.change(await screen.findByLabelText("Verify audit packet"), { target: { files: [jsonFile(packet)] } });

    expect(await screen.findByText("Packet requires review")).toBeInTheDocument();
    expect(screen.getByText("FAIL")).toBeInTheDocument();
    expect(screen.getByText("Integrity digest does not match.")).toBeInTheDocument();
  });

  it("rejects invalid JSON before calling the verifier", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/research-projects") return response(projects);
      if (url.includes("research-evidence-provenance")) return response(ledger);
      return response({}, 500);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ResearchProvenanceSection />);
    const invalid = new File(["not-json"], "broken.json", { type: "application/json" });
    fireEvent.change(await screen.findByLabelText("Verify audit packet"), { target: { files: [invalid] } });

    expect(await screen.findByRole("alert")).toHaveTextContent("not a valid audit packet JSON document");
    expect(fetchMock.mock.calls.some(([input]) => String(input).endsWith("/verify"))).toBe(false);
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
