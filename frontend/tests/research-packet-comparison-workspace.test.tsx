import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ResearchPacketComparisonWorkspace } from "@/components/research-packet-comparison-workspace";

const packet = (value: number) => JSON.stringify({ content_sha256: "a".repeat(64), content: { schema_version: "1.0", value } });

describe("ResearchPacketComparisonWorkspace", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("validates both packet inputs", async () => {
    render(<ResearchPacketComparisonWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Compare packets" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Enter two valid exported packets");
  });

  it("submits both packets and renders deterministic differences", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        status: "different",
        left_computed_sha256: "1".repeat(64),
        right_computed_sha256: "2".repeat(64),
        left_hash_matches: false,
        right_hash_matches: true,
        left_schema_version: "1.0",
        right_schema_version: "1.0",
        supported_schema_versions: ["1.0"],
        differences: [{ path: "value", kind: "changed" }],
        added_count: 0,
        removed_count: 0,
        changed_count: 1,
        detail: "The packet content contains structural differences.",
        disclaimer: "Does not judge truth or quality.",
      }),
    }));

    render(<ResearchPacketComparisonWorkspace />);
    fireEvent.change(screen.getByLabelText("Earlier packet JSON"), { target: { value: packet(1) } });
    fireEvent.change(screen.getByLabelText("Later packet JSON"), { target: { value: packet(2) } });
    fireEvent.click(screen.getByRole("button", { name: "Compare packets" }));

    expect(await screen.findByRole("heading", { name: "Comparison status: different" })).toBeInTheDocument();
    expect(screen.getByText("value")).toBeInTheDocument();
    expect(screen.getByText(/Added: 0 · Removed: 0 · Changed: 1/)).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith("/api/research-packet-comparison", expect.objectContaining({ method: "POST" }));
  });

  it("loads packet text from a local file", async () => {
    render(<ResearchPacketComparisonWorkspace />);
    const file = new File([packet(1)], "earlier.json", { type: "application/json" });
    fireEvent.change(screen.getByLabelText("Load earlier JSON"), { target: { files: [file] } });
    await waitFor(() => expect(screen.getByLabelText("Earlier packet JSON")).toHaveValue(packet(1)));
  });
});
