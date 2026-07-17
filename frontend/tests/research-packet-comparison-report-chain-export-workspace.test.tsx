import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { ResearchPacketComparisonReportChainExportWorkspace } from "../components/research-packet-comparison-report-chain-export-workspace";

const packet = {
  content_sha256: "a".repeat(64),
  content: { schema_version: "1.0", value: 1 },
};

const report = {
  report_sha256: "b".repeat(64),
  content: {
    schema_version: "1.0",
    report_type: "research_packet_comparison",
    status: "identical",
    left_supplied_sha256: "a".repeat(64),
    left_computed_sha256: "a".repeat(64),
    left_hash_matches: true,
    right_supplied_sha256: "a".repeat(64),
    right_computed_sha256: "a".repeat(64),
    right_hash_matches: true,
    left_schema_version: "1.0",
    right_schema_version: "1.0",
    supported_schema_versions: ["1.0"],
    added_count: 0,
    removed_count: 0,
    changed_count: 0,
    differences: [],
    detail: "The packet content is structurally identical.",
    disclaimer: "Structural comparison only.",
  },
};

function enterInputs() {
  fireEvent.change(screen.getByLabelText("Earlier packet JSON"), {
    target: { value: JSON.stringify(packet) },
  });
  fireEvent.change(screen.getByLabelText("Later packet JSON"), {
    target: { value: JSON.stringify(packet) },
  });
  fireEvent.change(screen.getByLabelText("Comparison report JSON"), {
    target: { value: JSON.stringify(report) },
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
});

test("exports and displays a deterministic chain verification report", async () => {
  const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        verification_report_sha256: "c".repeat(64),
        content: {
          schema_version: "1.0",
          report_type: "research_packet_comparison_chain_verification",
          chain_status: "consistent",
          left_hash_matches: true,
          right_hash_matches: true,
          comparison_report_hash_matches: true,
          failed_checks: [],
          detail: "The packets and comparison report form a consistent integrity chain.",
          disclaimer: "Integrity verification only.",
        },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  render(<ResearchPacketComparisonReportChainExportWorkspace />);
  enterInputs();
  fireEvent.click(screen.getByRole("button", { name: "Export verification report" }));

  await waitFor(() =>
    expect(screen.getByText("Chain status: consistent")).toBeInTheDocument(),
  );
  expect(screen.getByText("c".repeat(64))).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/research-packet-comparison-report-chain-export",
    expect.objectContaining({ method: "POST" }),
  );
  expect(screen.getByRole("button", { name: "Download JSON report" })).toBeInTheDocument();
});

test("rejects invalid input before requesting export", () => {
  const fetchMock = vi.spyOn(global, "fetch");
  render(<ResearchPacketComparisonReportChainExportWorkspace />);
  fireEvent.click(screen.getByRole("button", { name: "Export verification report" }));

  expect(
    screen.getByText("Enter two valid exported packets and one valid comparison report."),
  ).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();
});

test("displays failed checks for an inconsistent exported report", async () => {
  vi.spyOn(global, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        verification_report_sha256: "d".repeat(64),
        content: {
          schema_version: "1.0",
          report_type: "research_packet_comparison_chain_verification",
          chain_status: "inconsistent",
          left_hash_matches: true,
          right_hash_matches: false,
          comparison_report_hash_matches: true,
          failed_checks: ["right_packet_hash", "report_right_hash_flag"],
          detail: "The packets and comparison report do not form a consistent integrity chain.",
          disclaimer: "Integrity verification only.",
        },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  render(<ResearchPacketComparisonReportChainExportWorkspace />);
  enterInputs();
  fireEvent.click(screen.getByRole("button", { name: "Export verification report" }));

  await waitFor(() =>
    expect(screen.getByText("Chain status: inconsistent")).toBeInTheDocument(),
  );
  expect(screen.getByText("right_packet_hash")).toBeInTheDocument();
  expect(screen.getByText("report_right_hash_flag")).toBeInTheDocument();
});
