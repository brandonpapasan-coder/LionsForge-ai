import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { ResearchPacketComparisonReportWorkspace } from "../components/research-packet-comparison-report-workspace";

const packet = JSON.stringify({
  content_sha256: "a".repeat(64),
  content: { schema_version: "1.0", title: "Earlier" },
});

beforeEach(() => {
  vi.restoreAllMocks();
});

test("validates both packet inputs", async () => {
  render(<ResearchPacketComparisonReportWorkspace />);
  fireEvent.click(
    screen.getByRole("button", { name: "Create comparison report" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Enter two valid exported packets",
  );
});

test("creates and displays a comparison report", async () => {
  vi.spyOn(global, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        report_sha256: "b".repeat(64),
        content: {
          schema_version: "1.0",
          report_type: "research_packet_comparison",
          status: "different",
          left_hash_matches: true,
          right_hash_matches: false,
          added_count: 1,
          removed_count: 0,
          changed_count: 1,
          differences: [{ path: "title", kind: "changed" }],
          detail: "The packet content contains structural differences.",
          disclaimer: "This report records structural content differences only.",
        },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  render(<ResearchPacketComparisonReportWorkspace />);
  fireEvent.change(screen.getByLabelText("Earlier packet JSON"), {
    target: { value: packet },
  });
  fireEvent.change(screen.getByLabelText("Later packet JSON"), {
    target: { value: packet },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Create comparison report" }),
  );

  expect(
    await screen.findByText("Report status: different"),
  ).toBeInTheDocument();
  expect(screen.getByText("title")).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Download JSON report" }),
  ).toBeInTheDocument();
  expect(global.fetch).toHaveBeenCalledWith(
    "/api/research-packet-comparison-report",
    expect.objectContaining({ method: "POST" }),
  );
});

test("loads a local JSON packet file", async () => {
  render(<ResearchPacketComparisonReportWorkspace />);
  const file = new File([packet], "packet.json", {
    type: "application/json",
  });
  fireEvent.change(screen.getByLabelText("Load earlier JSON"), {
    target: { files: [file] },
  });
  await waitFor(() =>
    expect(screen.getByLabelText("Earlier packet JSON")).toHaveValue(packet),
  );
});
