import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CrossInvestigationReviewQueuePanel } from "@/components/cross-investigation-review-queue";

function response(body: unknown, status = 200, headers: Record<string, string> = {}) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    blob: async () => new Blob([JSON.stringify(body)], { type: "application/json" }),
    headers: new Headers(headers),
  });
}

function jsonFile(body: unknown, name = "report.json") {
  const content = typeof body === "string" ? body : JSON.stringify(body);
  const file = new File([content], name, { type: "application/json" });
  Object.defineProperty(file, "text", { value: async () => content });
  return file;
}

const queue = {
  contract_version: "1.0",
  status: "empty",
  item_count: 0,
  generated_from: "stored_owner_investigation_records",
  interpretation_notice: "Workflow only.",
  items: [],
};

const report = {
  contract_version: "1.0",
  artifact_type: "cross_investigation_review_queue_comparison_report",
  generated_from: "verified_snapshot_comparison",
  generated_at: "2026-07-26T00:00:00Z",
  content_sha256: "report-digest",
  interpretation_notice: "Integrity only.",
  comparison: {
    contract_version: "1.0",
    artifact_type: "cross_investigation_review_queue_snapshot_comparison",
    prior_content_sha256: "prior-digest",
    current_content_sha256: "current-digest",
    added_items: [], removed_items: [], unchanged_items: [],
    prior_reason_counts: {}, current_reason_counts: {}, reason_count_deltas: {},
    prior_investigation_count: 0, current_investigation_count: 0,
    investigation_count_delta: 0,
    interpretation_notice: "Workflow state only.",
  },
};

const verification = {
  contract_version: "1.0",
  artifact_type: "cross_investigation_review_queue_comparison_report_verification",
  valid: true,
  supplied_content_sha256: "report-digest",
  recomputed_content_sha256: "report-digest",
  prior_content_sha256: "prior-digest",
  current_content_sha256: "current-digest",
  added_item_count: 0, removed_item_count: 0, unchanged_item_count: 0,
  reason_count_deltas: {}, investigation_count_delta: 0,
  current_state_checked: false,
  interpretation_notice: "Canonical digest only.",
};

const receipt = {
  artifact_type: "cross_investigation_review_queue_comparison_verification_receipt",
  verified_report_content_sha256: "report-digest",
  content_sha256: "receipt-digest",
};

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

function installDownloadSpies() {
  const createObjectURL = vi.fn(() => "blob:receipt");
  const revokeObjectURL = vi.fn();
  vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
  let downloadedFilename = "";
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
    downloadedFilename = this.download;
  });
  return { createObjectURL, click, downloadedFilename: () => downloadedFilename };
}

async function verifyReport(user: ReturnType<typeof userEvent.setup>) {
  await user.upload(await screen.findByLabelText("Comparison report JSON"), jsonFile(report));
  await user.click(screen.getByRole("button", { name: "Verify comparison report" }));
  await screen.findByLabelText("Comparison report verification results");
}

describe("comparison verification receipt", () => {
  it("downloads a receipt with backend filename and digest using the verified payload", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn()
      .mockImplementationOnce(() => response(queue))
      .mockImplementationOnce(() => response(verification))
      .mockImplementationOnce(() => response(receipt, 200, {
        "content-disposition": "attachment; filename=\"verified-receipt.json\"",
        "x-content-sha256": "receipt-digest",
      }));
    vi.stubGlobal("fetch", fetchMock);
    const download = installDownloadSpies();
    render(<CrossInvestigationReviewQueuePanel />);

    await verifyReport(user);
    await user.click(screen.getByRole("button", { name: "Download verification receipt" }));

    expect(download.downloadedFilename()).toBe("verified-receipt.json");
    expect(screen.getByLabelText("Verification receipt digest")).toHaveTextContent("receipt-digest");
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/investigations/review-queue/snapshot/compare/report/verify/receipt",
      expect.objectContaining({ method: "POST", body: JSON.stringify(report) }),
    );
  });

  it("uses the deterministic fallback filename", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn()
      .mockImplementationOnce(() => response(queue))
      .mockImplementationOnce(() => response(verification))
      .mockImplementationOnce(() => response(receipt)));
    const download = installDownloadSpies();
    render(<CrossInvestigationReviewQueuePanel />);

    await verifyReport(user);
    await user.click(screen.getByRole("button", { name: "Download verification receipt" }));

    expect(download.downloadedFilename()).toBe("lionsforge-comparison-verification-receipt.json");
  });

  it("does not download when receipt export fails", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn()
      .mockImplementationOnce(() => response(queue))
      .mockImplementationOnce(() => response(verification))
      .mockImplementationOnce(() => response({ detail: "Comparison report digest does not match its canonical payload" }, 400)));
    const download = installDownloadSpies();
    render(<CrossInvestigationReviewQueuePanel />);

    await verifyReport(user);
    await user.click(screen.getByRole("button", { name: "Download verification receipt" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No file was downloaded");
    expect(download.createObjectURL).not.toHaveBeenCalled();
    expect(download.click).not.toHaveBeenCalled();
  });

  it("revokes receipt eligibility and clears the prior digest when a new file is selected", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn()
      .mockImplementationOnce(() => response(queue))
      .mockImplementationOnce(() => response(verification))
      .mockImplementationOnce(() => response(receipt, 200, { "x-content-sha256": "receipt-digest" })));
    installDownloadSpies();
    render(<CrossInvestigationReviewQueuePanel />);

    const selector = await screen.findByLabelText("Comparison report JSON");
    await user.upload(selector, jsonFile(report, "first.json"));
    await user.click(screen.getByRole("button", { name: "Verify comparison report" }));
    await user.click(await screen.findByRole("button", { name: "Download verification receipt" }));
    expect(await screen.findByLabelText("Verification receipt digest")).toBeInTheDocument();

    await user.upload(selector, jsonFile({ ...report, content_sha256: "other" }, "second.json"));
    expect(screen.queryByRole("button", { name: "Download verification receipt" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Verification receipt digest")).not.toBeInTheDocument();
  });
});
