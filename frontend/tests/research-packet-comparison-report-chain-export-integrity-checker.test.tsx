import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { ResearchPacketComparisonReportChainExportIntegrityChecker } from "../components/research-packet-comparison-report-chain-export-integrity-checker";

const report = {
  verification_report_sha256: "a".repeat(64),
  content: {
    schema_version: "1.0",
    report_type: "research_packet_comparison_chain_verification",
    chain_status: "consistent",
  },
};

beforeEach(() => {
  vi.restoreAllMocks();
});

test("submits a verification report and displays matching integrity", async () => {
  const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "matching",
        supplied_sha256: "a".repeat(64),
        computed_sha256: "a".repeat(64),
        schema_version: "1.0",
        report_type: "research_packet_comparison_chain_verification",
        supported_schema_versions: ["1.0"],
        supported_report_types: ["research_packet_comparison_chain_verification"],
        detail: "The verification report content matches the supplied SHA-256 value.",
        disclaimer: "Integrity verification only.",
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  render(<ResearchPacketComparisonReportChainExportIntegrityChecker />);
  fireEvent.change(screen.getByLabelText("Verification report JSON"), {
    target: { value: JSON.stringify(report) },
  });
  fireEvent.click(screen.getByRole("button", { name: "Check report integrity" }));

  await waitFor(() =>
    expect(screen.getByText("Integrity status: matching")).toBeInTheDocument(),
  );
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/research-packet-comparison-report-chain-export-integrity",
    expect.objectContaining({ method: "POST" }),
  );
});

test("rejects invalid report input before making a request", () => {
  const fetchMock = vi.spyOn(global, "fetch");
  render(<ResearchPacketComparisonReportChainExportIntegrityChecker />);
  fireEvent.click(screen.getByRole("button", { name: "Check report integrity" }));

  expect(
    screen.getByText(
      "Enter a valid verification report containing verification_report_sha256 and content.",
    ),
  ).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();
});

test("displays unsupported schema and report type guidance", async () => {
  vi.spyOn(global, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "unsupported",
        supplied_sha256: "a".repeat(64),
        computed_sha256: "b".repeat(64),
        schema_version: "2.0",
        report_type: "unknown",
        supported_schema_versions: ["1.0"],
        supported_report_types: ["research_packet_comparison_chain_verification"],
        detail: "The verification report schema version or report type is unsupported.",
        disclaimer: "Integrity verification only.",
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  render(<ResearchPacketComparisonReportChainExportIntegrityChecker />);
  fireEvent.change(screen.getByLabelText("Verification report JSON"), {
    target: { value: JSON.stringify(report) },
  });
  fireEvent.click(screen.getByRole("button", { name: "Check report integrity" }));

  await waitFor(() =>
    expect(screen.getByText("Integrity status: unsupported")).toBeInTheDocument(),
  );
  expect(screen.getByText("Supported schemas: 1.0")).toBeInTheDocument();
  expect(
    screen.getByText(
      "Supported report types: research_packet_comparison_chain_verification",
    ),
  ).toBeInTheDocument();
});
