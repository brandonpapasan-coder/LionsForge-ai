import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { ResearchPacketComparisonReportIntegrityChecker } from "../components/research-packet-comparison-report-integrity-checker";

const report = JSON.stringify({
  report_sha256: "a".repeat(64),
  content: {
    schema_version: "1.0",
    report_type: "research_packet_comparison",
    status: "different",
  },
});

beforeEach(() => {
  vi.restoreAllMocks();
});

test("validates comparison report input", async () => {
  render(<ResearchPacketComparisonReportIntegrityChecker />);
  fireEvent.click(
    screen.getByRole("button", { name: "Check report integrity" }),
  );

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Enter a valid comparison report",
  );
});

test("checks and displays matching report integrity", async () => {
  vi.spyOn(global, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "matching",
        supplied_sha256: "a".repeat(64),
        computed_sha256: "a".repeat(64),
        schema_version: "1.0",
        report_type: "research_packet_comparison",
        supported_schema_versions: ["1.0"],
        supported_report_types: ["research_packet_comparison"],
        detail: "The comparison report content matches the supplied SHA-256 value.",
        disclaimer: "This check does not certify truth.",
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  render(<ResearchPacketComparisonReportIntegrityChecker />);
  fireEvent.change(screen.getByLabelText("Comparison report JSON"), {
    target: { value: report },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Check report integrity" }),
  );

  expect(await screen.findByText("Integrity status: matching")).toBeInTheDocument();
  expect(screen.getByText("Report type: research_packet_comparison")).toBeInTheDocument();
  expect(global.fetch).toHaveBeenCalledWith(
    "/api/research-packet-comparison-report-integrity",
    expect.objectContaining({ method: "POST" }),
  );
});

test("loads a local comparison report file", async () => {
  render(<ResearchPacketComparisonReportIntegrityChecker />);
  const file = new File([report], "comparison-report.json", {
    type: "application/json",
  });
  fireEvent.change(screen.getByLabelText("Load comparison report"), {
    target: { files: [file] },
  });

  await waitFor(() =>
    expect(screen.getByLabelText("Comparison report JSON")).toHaveValue(report),
  );
});
