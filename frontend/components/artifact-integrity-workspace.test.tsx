import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ArtifactIntegrityWorkspace } from "@/components/artifact-integrity-workspace";

function response(body: unknown, status = 200) {
  return Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body });
}

function jsonFile(body: unknown, name = "artifact.json") {
  const content = typeof body === "string" ? body : JSON.stringify(body);
  const file = new File([content], name, { type: "application/json" });
  Object.defineProperty(file, "text", { value: async () => content });
  return file;
}

const report = { contract_version: "1.0", artifact_type: "cross_investigation_review_queue_comparison_report", content_sha256: "report-digest" };
const receipt = { contract_version: "1.0", artifact_type: "cross_investigation_review_queue_comparison_verification_receipt", content_sha256: "receipt-digest" };
const common = { valid: true, supplied_content_sha256: "digest", prior_content_sha256: "prior", current_content_sha256: "current", added_item_count: 2, removed_item_count: 1, unchanged_item_count: 4, reason_count_deltas: { missing_validation: 2 }, investigation_count_delta: 1, current_state_checked: false, interpretation_notice: "Integrity only." };
const reportResult = { contract_version: "1.0", artifact_type: "cross_investigation_review_queue_artifact_integrity_result", detected_artifact_type: report.artifact_type, valid: true, current_state_checked: false, interpretation_notice: "Workspace integrity only.", validation: { ...common, artifact_type: "cross_investigation_review_queue_comparison_report_verification", recomputed_content_sha256: "report-digest" } };
const receiptResult = { contract_version: "1.0", artifact_type: "cross_investigation_review_queue_artifact_integrity_result", detected_artifact_type: receipt.artifact_type, valid: true, current_state_checked: false, interpretation_notice: "Workspace integrity only.", validation: { ...common, artifact_type: "cross_investigation_review_queue_comparison_verification_receipt_validation", recomputed_content_sha256: "receipt-digest", verified_report_content_sha256: "report-digest", verification_contract_version: "1.0", verification_artifact_type: "cross_investigation_review_queue_comparison_report_verification" } };

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("artifact integrity workspace", () => {
  it("detects and renders a comparison report", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(() => response(reportResult));
    vi.stubGlobal("fetch", fetchMock);
    render(<ArtifactIntegrityWorkspace />);
    await user.upload(screen.getByLabelText("Review-queue artifact JSON"), jsonFile(report));
    await user.click(screen.getByRole("button", { name: "Validate artifact" }));
    const results = await screen.findByLabelText("Artifact integrity results");
    expect(results).toHaveTextContent("comparison report");
    expect(results).toHaveTextContent("report-digest");
    expect(results).not.toHaveTextContent("Verified report SHA-256");
    expect(fetchMock).toHaveBeenCalledWith("/api/investigations/review-queue/artifacts/validate", expect.objectContaining({ body: JSON.stringify(report) }));
  });

  it("detects and renders a verification receipt", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn(() => response(receiptResult)));
    render(<ArtifactIntegrityWorkspace />);
    await user.upload(screen.getByLabelText("Review-queue artifact JSON"), jsonFile(receipt));
    await user.click(screen.getByRole("button", { name: "Validate artifact" }));
    const results = await screen.findByLabelText("Artifact integrity results");
    expect(results).toHaveTextContent("verification receipt");
    expect(results).toHaveTextContent("receipt-digest");
    expect(results).toHaveTextContent("Verified report SHA-256");
    expect(results).toHaveTextContent("Current queue checked: no");
  });

  it("rejects malformed JSON before submission", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<ArtifactIntegrityWorkspace />);
    await user.upload(screen.getByLabelText("Review-queue artifact JSON"), jsonFile("{broken"));
    await user.click(screen.getByRole("button", { name: "Validate artifact" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("not valid JSON");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows backend rejection details without stale success", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn(() => response({ detail: "Artifact type is unsupported" }, 422)));
    render(<ArtifactIntegrityWorkspace />);
    await user.upload(screen.getByLabelText("Review-queue artifact JSON"), jsonFile({ artifact_type: "other" }));
    await user.click(screen.getByRole("button", { name: "Validate artifact" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("unsupported");
    expect(screen.queryByLabelText("Artifact integrity results")).not.toBeInTheDocument();
  });

  it("shows digest mismatch details", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn(() => response({ detail: "Comparison report digest does not match" }, 400)));
    render(<ArtifactIntegrityWorkspace />);
    await user.upload(screen.getByLabelText("Review-queue artifact JSON"), jsonFile(report));
    await user.click(screen.getByRole("button", { name: "Validate artifact" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("digest does not match");
  });

  it("handles unauthorized validation without showing protected metadata", async () => {
    const user = userEvent.setup();
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.stubGlobal("fetch", vi.fn(() => response({ detail: "Not authenticated" }, 401)));
    render(<ArtifactIntegrityWorkspace />);
    await user.upload(screen.getByLabelText("Review-queue artifact JSON"), jsonFile(report));
    await user.click(screen.getByRole("button", { name: "Validate artifact" }));
    expect(screen.queryByLabelText("Artifact integrity results")).not.toBeInTheDocument();
  });

  it("shows retry guidance on transport failure", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    render(<ArtifactIntegrityWorkspace />);
    await user.upload(screen.getByLabelText("Review-queue artifact JSON"), jsonFile(report));
    await user.click(screen.getByRole("button", { name: "Validate artifact" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Retry validation");
  });

  it("clears prior results when a new artifact is selected", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn(() => response(reportResult)));
    render(<ArtifactIntegrityWorkspace />);
    const selector = screen.getByLabelText("Review-queue artifact JSON");
    await user.upload(selector, jsonFile(report, "first.json"));
    await user.click(screen.getByRole("button", { name: "Validate artifact" }));
    expect(await screen.findByLabelText("Artifact integrity results")).toBeInTheDocument();
    await user.upload(selector, jsonFile(receipt, "second.json"));
    expect(screen.queryByLabelText("Artifact integrity results")).not.toBeInTheDocument();
  });
});
