import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { ResearchPacketComparisonReportChainExportIntegrityReceiptCheckWorkspace } from "../components/research-packet-comparison-report-chain-export-integrity-receipt-check-workspace";

const receipt = {
  integrity_receipt_sha256: "a".repeat(64),
  content: {
    schema_version: "1.0",
    report_type:
      "research_packet_comparison_chain_verification_integrity_receipt",
    integrity_status: "matching",
  },
};

function enterReceipt() {
  fireEvent.change(screen.getByLabelText("Integrity receipt JSON"), {
    target: { value: JSON.stringify(receipt) },
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
});

test("checks and displays a matching integrity receipt", async () => {
  const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "matching",
        supplied_sha256: "a".repeat(64),
        computed_sha256: "a".repeat(64),
        schema_version: "1.0",
        report_type:
          "research_packet_comparison_chain_verification_integrity_receipt",
        supported_schema_versions: ["1.0"],
        supported_report_types: [
          "research_packet_comparison_chain_verification_integrity_receipt",
        ],
        detail: "The integrity receipt content matches the supplied SHA-256 value.",
        disclaimer: "This check does not certify truth or approval.",
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  render(
    <ResearchPacketComparisonReportChainExportIntegrityReceiptCheckWorkspace />,
  );
  enterReceipt();
  fireEvent.click(screen.getByRole("button", { name: "Check integrity receipt" }));

  await waitFor(() =>
    expect(screen.getByText("Integrity status: matching")).toBeInTheDocument(),
  );
  expect(screen.getAllByText("a".repeat(64))).toHaveLength(2);
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/research-packet-comparison-report-chain-export-integrity-receipt-check",
    expect.objectContaining({ method: "POST" }),
  );
});

test("rejects invalid input before requesting a check", () => {
  const fetchMock = vi.spyOn(global, "fetch");
  render(
    <ResearchPacketComparisonReportChainExportIntegrityReceiptCheckWorkspace />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Check integrity receipt" }));

  expect(
    screen.getByText(
      "Enter a valid integrity receipt containing integrity_receipt_sha256 and content.",
    ),
  ).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();
});

test("displays a changed receipt with differing hashes", async () => {
  vi.spyOn(global, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        status: "changed",
        supplied_sha256: "a".repeat(64),
        computed_sha256: "b".repeat(64),
        schema_version: "1.0",
        report_type:
          "research_packet_comparison_chain_verification_integrity_receipt",
        supported_schema_versions: ["1.0"],
        supported_report_types: [
          "research_packet_comparison_chain_verification_integrity_receipt",
        ],
        detail: "The integrity receipt content does not match the supplied SHA-256 value.",
        disclaimer: "This check does not certify truth or approval.",
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  render(
    <ResearchPacketComparisonReportChainExportIntegrityReceiptCheckWorkspace />,
  );
  enterReceipt();
  fireEvent.click(screen.getByRole("button", { name: "Check integrity receipt" }));

  await waitFor(() =>
    expect(screen.getByText("Integrity status: changed")).toBeInTheDocument(),
  );
  expect(screen.getByText("b".repeat(64))).toBeInTheDocument();
});
