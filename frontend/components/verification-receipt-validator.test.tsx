import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { VerificationReceiptValidator } from "@/components/verification-receipt-validator";

function response(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

function jsonFile(body: unknown, name = "receipt.json") {
  const content = typeof body === "string" ? body : JSON.stringify(body);
  const file = new File([content], name, { type: "application/json" });
  Object.defineProperty(file, "text", { value: async () => content });
  return file;
}

const receipt = {
  contract_version: "1.0",
  artifact_type: "cross_investigation_review_queue_comparison_verification_receipt",
  verified_report_content_sha256: "report-digest",
  prior_content_sha256: "prior-digest",
  current_content_sha256: "current-digest",
  added_item_count: 2,
  removed_item_count: 1,
  unchanged_item_count: 4,
  reason_count_deltas: { missing_validation: 2, stale_validation: -1 },
  investigation_count_delta: 1,
  verification_contract_version: "1.0",
  verification_artifact_type: "cross_investigation_review_queue_comparison_report_verification",
  current_state_checked: false,
  generated_from: "successful_report_contract_and_digest_verification",
  interpretation_notice: "Artifact integrity only.",
  generated_at: "2026-07-26T00:00:00Z",
  content_sha256: "receipt-digest",
};

const validation = {
  contract_version: "1.0",
  artifact_type: "cross_investigation_review_queue_comparison_verification_receipt_validation",
  valid: true,
  supplied_content_sha256: "receipt-digest",
  recomputed_content_sha256: "receipt-digest",
  verified_report_content_sha256: "report-digest",
  prior_content_sha256: "prior-digest",
  current_content_sha256: "current-digest",
  added_item_count: 2,
  removed_item_count: 1,
  unchanged_item_count: 4,
  reason_count_deltas: { missing_validation: 2, stale_validation: -1 },
  investigation_count_delta: 1,
  verification_contract_version: "1.0",
  verification_artifact_type: "cross_investigation_review_queue_comparison_report_verification",
  current_state_checked: false,
  interpretation_notice: "Canonical digest only; no agreement with current queue state.",
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("verification receipt validator", () => {
  it("validates a receipt and displays only bound metadata", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(() => response(validation));
    vi.stubGlobal("fetch", fetchMock);
    render(<VerificationReceiptValidator />);

    await user.upload(screen.getByLabelText("Verification receipt JSON"), jsonFile(receipt));
    await user.click(screen.getByRole("button", { name: "Validate verification receipt" }));

    const results = await screen.findByLabelText("Verification receipt validation results");
    expect(results).toHaveTextContent("Receipt integrity: valid");
    expect(results).toHaveTextContent("receipt-digest");
    expect(results).toHaveTextContent("report-digest");
    expect(results).toHaveTextContent("prior-digest");
    expect(results).toHaveTextContent("current-digest");
    expect(results).toHaveTextContent("missing validation: +2");
    expect(results).toHaveTextContent("stale validation: -1");
    expect(results).toHaveTextContent("Current queue checked: no");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/investigations/review-queue/snapshot/compare/report/verify/receipt/validate",
      expect.objectContaining({ method: "POST", body: JSON.stringify(receipt) }),
    );
  });

  it("rejects malformed JSON before a network request", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<VerificationReceiptValidator />);

    await user.upload(screen.getByLabelText("Verification receipt JSON"), jsonFile("{broken"));
    await user.click(screen.getByRole("button", { name: "Validate verification receipt" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("not valid JSON");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows digest mismatch details without displaying stale success", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn(() => response({ detail: "Verification receipt digest does not match its canonical payload" }, 400)));
    render(<VerificationReceiptValidator />);

    await user.upload(screen.getByLabelText("Verification receipt JSON"), jsonFile(receipt));
    await user.click(screen.getByRole("button", { name: "Validate verification receipt" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("digest does not match");
    expect(screen.queryByLabelText("Verification receipt validation results")).not.toBeInTheDocument();
  });

  it("shows unsupported-contract guidance", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn(() => response({}, 422)));
    render(<VerificationReceiptValidator />);

    await user.upload(screen.getByLabelText("Verification receipt JSON"), jsonFile(receipt));
    await user.click(screen.getByRole("button", { name: "Validate verification receipt" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("unsupported");
  });

  it("handles unauthorized validation without showing protected metadata", async () => {
    const user = userEvent.setup();
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.stubGlobal("fetch", vi.fn(() => response({ detail: "Not authenticated" }, 401)));
    render(<VerificationReceiptValidator />);

    await user.upload(screen.getByLabelText("Verification receipt JSON"), jsonFile(receipt));
    await user.click(screen.getByRole("button", { name: "Validate verification receipt" }));

    expect(screen.queryByLabelText("Verification receipt validation results")).not.toBeInTheDocument();
    expect(consoleError).toHaveBeenCalled();
  });

  it("shows retry guidance on transport failure", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    render(<VerificationReceiptValidator />);

    await user.upload(screen.getByLabelText("Verification receipt JSON"), jsonFile(receipt));
    await user.click(screen.getByRole("button", { name: "Validate verification receipt" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Retry validation");
  });

  it("clears a prior validation result when a new receipt is selected", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn(() => response(validation)));
    render(<VerificationReceiptValidator />);

    const selector = screen.getByLabelText("Verification receipt JSON");
    await user.upload(selector, jsonFile(receipt, "first.json"));
    await user.click(screen.getByRole("button", { name: "Validate verification receipt" }));
    expect(await screen.findByLabelText("Verification receipt validation results")).toBeInTheDocument();

    await user.upload(selector, jsonFile({ ...receipt, content_sha256: "other" }, "second.json"));
    expect(screen.queryByLabelText("Verification receipt validation results")).not.toBeInTheDocument();
  });
});