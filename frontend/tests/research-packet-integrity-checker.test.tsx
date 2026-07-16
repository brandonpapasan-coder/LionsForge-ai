import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchPacketIntegrityChecker } from "@/components/research-packet-integrity-checker";

const packet = { content_sha256: "a".repeat(64), content: { schema_version: "1.0", project_id: 7 } };
const result = {
  status: "matching",
  supplied_sha256: "a".repeat(64),
  computed_sha256: "a".repeat(64),
  schema_version: "1.0",
  supported_schema_versions: ["1.0"],
  detail: "The packet content matches the supplied SHA-256 value.",
  disclaimer: "This check does not certify truth, quality, authorship, approval, or publication status.",
};
const response = (body: unknown, status = 200) => Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body });

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("ResearchPacketIntegrityChecker", () => {
  it("submits pasted packet JSON and renders matching results", async () => {
    const fetchMock = vi.fn(() => response(result));
    vi.stubGlobal("fetch", fetchMock);
    render(<ResearchPacketIntegrityChecker />);

    fireEvent.change(screen.getByLabelText("Packet JSON"), { target: { value: JSON.stringify(packet) } });
    fireEvent.click(screen.getByRole("button", { name: "Check integrity" }));

    expect(await screen.findByText("Integrity status: matching")).toBeInTheDocument();
    expect(screen.getByText(result.detail)).toBeInTheDocument();
    expect(screen.getAllByText("a".repeat(64))).toHaveLength(2);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/research-packet-integrity", expect.objectContaining({ method: "POST" })));
  });

  it("rejects malformed packet JSON before calling the API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<ResearchPacketIntegrityChecker />);

    fireEvent.change(screen.getByLabelText("Packet JSON"), { target: { value: "not-json" } });
    fireEvent.click(screen.getByRole("button", { name: "Check integrity" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("valid exported packet");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("loads a local JSON packet file", async () => {
    render(<ResearchPacketIntegrityChecker />);
    const file = new File([JSON.stringify(packet)], "packet.json", { type: "application/json" });

    fireEvent.change(screen.getByLabelText("Load JSON packet"), { target: { files: [file] } });

    await waitFor(() => expect(screen.getByLabelText("Packet JSON")).toHaveValue(JSON.stringify(packet)));
  });

  it("renders unsupported schema details", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({ ...result, status: "unsupported", schema_version: "2.0", supported_schema_versions: ["1.0"] })));
    render(<ResearchPacketIntegrityChecker />);
    fireEvent.change(screen.getByLabelText("Packet JSON"), { target: { value: JSON.stringify(packet) } });
    fireEvent.click(screen.getByRole("button", { name: "Check integrity" }));

    expect(await screen.findByText("Integrity status: unsupported")).toBeInTheDocument();
    expect(screen.getByText("Supported schemas: 1.0")).toBeInTheDocument();
  });

  it("surfaces verification failures", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({}, 500)));
    render(<ResearchPacketIntegrityChecker />);
    fireEvent.change(screen.getByLabelText("Packet JSON"), { target: { value: JSON.stringify(packet) } });
    fireEvent.click(screen.getByRole("button", { name: "Check integrity" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("could not be completed");
  });
});
