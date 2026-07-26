import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CrossInvestigationReviewQueuePanel } from "@/components/cross-investigation-review-queue";

function response(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    headers: new Headers({ "content-type": "application/json" }),
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
    added_items: [],
    removed_items: [],
    unchanged_items: [],
    prior_reason_counts: {},
    current_reason_counts: { missing_validation: 2 },
    reason_count_deltas: { missing_validation: 2 },
    prior_investigation_count: 0,
    current_investigation_count: 2,
    investigation_count_delta: 2,
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
  added_item_count: 0,
  removed_item_count: 0,
  unchanged_item_count: 0,
  reason_count_deltas: { missing_validation: 2 },
  investigation_count_delta: 2,
  current_state_checked: false,
  interpretation_notice: "Verification confirms the canonical digest only and does not check current queue state.",
};

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("comparison report verification", () => {
  it("verifies a valid private report and renders preserved metadata", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockImplementationOnce(() => response(queue)).mockImplementationOnce(() => response(verification));
    vi.stubGlobal("fetch", fetchMock);
    render(<CrossInvestigationReviewQueuePanel />);

    await user.upload(await screen.findByLabelText("Comparison report JSON"), jsonFile(report));
    await user.click(screen.getByRole("button", { name: "Verify comparison report" }));

    const results = await screen.findByLabelText("Comparison report verification results");
    expect(results).toHaveTextContent("Artifact integrity: valid");
    expect(results).toHaveTextContent("report-digest");
    expect(results).toHaveTextContent("prior-digest");
    expect(results).toHaveTextContent("current-digest");
    expect(results).toHaveTextContent("missing validation: +2");
    expect(results).toHaveTextContent("Current queue checked: no");
    expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/investigations/review-queue/snapshot/compare/report/verify",
      expect.objectContaining({ method: "POST", body: JSON.stringify(report) }),
    );
  });

  it("rejects malformed report JSON before network submission", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(() => response(queue));
    vi.stubGlobal("fetch", fetchMock);
    render(<CrossInvestigationReviewQueuePanel />);

    await user.upload(await screen.findByLabelText("Comparison report JSON"), jsonFile("{"));
    await user.click(screen.getByRole("button", { name: "Verify comparison report" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("not valid JSON");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.queryByLabelText("Comparison report verification results")).not.toBeInTheDocument();
  });

  it("shows digest mismatch without rendering verification metadata", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn().mockImplementationOnce(() => response(queue)).mockImplementationOnce(() => response({ detail: "Comparison report digest does not match its canonical payload" }, 400)));
    render(<CrossInvestigationReviewQueuePanel />);

    await user.upload(await screen.findByLabelText("Comparison report JSON"), jsonFile(report));
    await user.click(screen.getByRole("button", { name: "Verify comparison report" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("digest does not match");
    expect(screen.queryByLabelText("Comparison report verification results")).not.toBeInTheDocument();
  });

  it("shows unsupported contract state", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn().mockImplementationOnce(() => response(queue)).mockImplementationOnce(() => response({ detail: [{ msg: "Input should be '1.0'" }] }, 422)));
    render(<CrossInvestigationReviewQueuePanel />);

    await user.upload(await screen.findByLabelText("Comparison report JSON"), jsonFile({ ...report, contract_version: "2.0" }));
    await user.click(screen.getByRole("button", { name: "Verify comparison report" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("unsupported");
  });

  it("clears a prior valid result when a new file is selected", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn().mockImplementationOnce(() => response(queue)).mockImplementationOnce(() => response(verification)));
    render(<CrossInvestigationReviewQueuePanel />);

    const selector = await screen.findByLabelText("Comparison report JSON");
    await user.upload(selector, jsonFile(report, "first.json"));
    await user.click(screen.getByRole("button", { name: "Verify comparison report" }));
    expect(await screen.findByLabelText("Comparison report verification results")).toBeInTheDocument();

    await user.upload(selector, jsonFile({ ...report, content_sha256: "other" }, "second.json"));
    expect(screen.queryByLabelText("Comparison report verification results")).not.toBeInTheDocument();
  });

  it("shows retry guidance after a transport failure", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn().mockImplementationOnce(() => response(queue)).mockRejectedValueOnce(new Error("offline")));
    render(<CrossInvestigationReviewQueuePanel />);

    await user.upload(await screen.findByLabelText("Comparison report JSON"), jsonFile(report));
    await user.click(screen.getByRole("button", { name: "Verify comparison report" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Retry verification");
  });
});
