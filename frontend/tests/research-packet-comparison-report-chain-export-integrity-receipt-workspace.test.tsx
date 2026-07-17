import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import { ResearchPacketComparisonReportChainExportIntegrityReceiptWorkspace } from "../components/research-packet-comparison-report-chain-export-integrity-receipt-workspace";

const verificationReport = {
  verification_report_sha256: "a".repeat(64),
  content: {
    schema_version: "1.0",
    report_type: "research_packet_comparison_chain_verification",
    chain_status: "consistent",
  },
};

function enterReport() {
  fireEvent.change(screen.getByLabelText("Verification report JSON"), {
    target: { value: JSON.stringify(verificationReport) },
  });
}

beforeEach(() => {
  vi.restoreAllMocks();
});

test("exports, displays, and downloads a deterministic integrity receipt", async () => {
  const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        integrity_receipt_sha256: "b".repeat(64),
        content: {
          schema_version: "1.0",
          report_type:
            "research_packet_comparison_chain_verification_integrity_receipt",
          integrity_status: "matching",
          supplied_sha256: "a".repeat(64),
          computed_sha256: "a".repeat(64),
          source_schema_version: "1.0",
          source_report_type:
            "research_packet_comparison_chain_verification",
          detail: "The chain-verification report content matches the supplied SHA-256 value.",
          disclaimer: "This check does not certify truth or approval.",
        },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );
  const createObjectURL = vi.fn(() => "blob:receipt");
  const revokeObjectURL = vi.fn();
  Object.defineProperty(URL, "createObjectURL", {
    configurable: true,
    value: createObjectURL,
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    configurable: true,
    value: revokeObjectURL,
  });
  const click = vi
    .spyOn(HTMLAnchorElement.prototype, "click")
    .mockImplementation(() => undefined);

  render(<ResearchPacketComparisonReportChainExportIntegrityReceiptWorkspace />);
  enterReport();
  fireEvent.click(screen.getByRole("button", { name: "Export integrity receipt" }));

  await waitFor(() =>
    expect(screen.getByText("Integrity status: matching")).toBeInTheDocument(),
  );
  expect(screen.getByText("b".repeat(64))).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/research-packet-comparison-report-chain-export-integrity-receipt",
    expect.objectContaining({ method: "POST" }),
  );

  fireEvent.click(screen.getByRole("button", { name: "Download JSON receipt" }));
  expect(createObjectURL).toHaveBeenCalledOnce();
  expect(click).toHaveBeenCalledOnce();
  expect(revokeObjectURL).toHaveBeenCalledWith("blob:receipt");
});

test("rejects invalid input before requesting receipt export", () => {
  const fetchMock = vi.spyOn(global, "fetch");
  render(<ResearchPacketComparisonReportChainExportIntegrityReceiptWorkspace />);
  fireEvent.click(screen.getByRole("button", { name: "Export integrity receipt" }));

  expect(
    screen.getByText(
      "Enter a valid verification report containing verification_report_sha256 and content.",
    ),
  ).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();
});

test("displays a changed integrity receipt with differing hashes", async () => {
  vi.spyOn(global, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        integrity_receipt_sha256: "c".repeat(64),
        content: {
          schema_version: "1.0",
          report_type:
            "research_packet_comparison_chain_verification_integrity_receipt",
          integrity_status: "changed",
          supplied_sha256: "a".repeat(64),
          computed_sha256: "d".repeat(64),
          source_schema_version: "1.0",
          source_report_type:
            "research_packet_comparison_chain_verification",
          detail: "The chain-verification report content does not match the supplied SHA-256 value.",
          disclaimer: "This check does not certify truth or approval.",
        },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    ),
  );

  render(<ResearchPacketComparisonReportChainExportIntegrityReceiptWorkspace />);
  enterReport();
  fireEvent.click(screen.getByRole("button", { name: "Export integrity receipt" }));

  await waitFor(() =>
    expect(screen.getByText("Integrity status: changed")).toBeInTheDocument(),
  );
  expect(screen.getByText("d".repeat(64))).toBeInTheDocument();
});
