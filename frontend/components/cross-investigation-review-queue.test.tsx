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

function jsonFile(body: unknown, name = "prior.json") {
  const content = typeof body === "string" ? body : JSON.stringify(body);
  const file = new File([content], name, { type: "application/json" });
  Object.defineProperty(file, "text", { value: async () => content });
  return file;
}

const queue = {
  contract_version: "1.0",
  status: "active",
  item_count: 3,
  generated_from: "stored_owner_investigation_records",
  interpretation_notice: "Workflow only.",
  items: [
    { item_key: "7:1:blocked_remediation", investigation_id: 7, investigation_title: "Alpha", investigation_status: "open", claim_id: 1, claim_statement: "Alpha claim", reason_type: "blocked_remediation", workflow_priority: 5, reason: "Stored remediation progress is blocked.", stored_inputs: ["remediation_status=blocked"], latest_relevant_at: "2026-07-25T18:00:00Z", source_tables: ["remediation_progress"], source_record_ids: [4] },
    { item_key: "7:1:missing_validation", investigation_id: 7, investigation_title: "Alpha", investigation_status: "open", claim_id: 1, claim_statement: "Alpha claim", reason_type: "missing_validation", workflow_priority: 4, reason: "No human validation judgment is stored for this claim.", stored_inputs: ["judgment_count=0"], latest_relevant_at: "2026-07-25T17:00:00Z", source_tables: ["investigation_claims"], source_record_ids: [1] },
    { item_key: "9:2:unresolved_contradiction", investigation_id: 9, investigation_title: "Beta", investigation_status: "in_review", claim_id: 2, claim_statement: "Beta claim", reason_type: "unresolved_contradiction", workflow_priority: 5, reason: "One or more stored evidence records contradict this claim.", stored_inputs: ["contradicting_evidence_count=1"], latest_relevant_at: "2026-07-25T16:00:00Z", source_tables: ["claim_evidence"], source_record_ids: [8] },
  ],
};

const snapshot = { artifact_type: "cross_investigation_review_queue_snapshot", queue, content_sha256: "abc123" };
const comparison = {
  contract_version: "1.0",
  artifact_type: "cross_investigation_review_queue_snapshot_comparison",
  prior_content_sha256: "prior",
  current_content_sha256: "current",
  added_items: [queue.items[0]],
  removed_items: [queue.items[1]],
  unchanged_items: [queue.items[2]],
  prior_reason_counts: { missing_validation: 1 },
  current_reason_counts: { blocked_remediation: 1 },
  reason_count_deltas: { blocked_remediation: 1, missing_validation: -1 },
  prior_investigation_count: 1,
  current_investigation_count: 2,
  investigation_count_delta: 1,
  interpretation_notice: "This comparison describes changes in stored workflow state only.",
};

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("CrossInvestigationReviewQueuePanel", () => {
  it("renders stored provenance, filters, and investigation navigation", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn(() => response(queue)));
    render(<CrossInvestigationReviewQueuePanel />);
    expect(await screen.findByText("Stored remediation progress is blocked.")).toBeInTheDocument();
    expect(screen.getAllByText(/not validation evidence or advice/)).toHaveLength(2);
    expect(screen.getByText(/remediation_progress record 4/)).toBeInTheDocument();
    expect(screen.getByText(/digest verifies export integrity only/)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Open investigation context" })).toHaveLength(3);
    await user.selectOptions(screen.getByLabelText("Review reason"), "unresolved_contradiction");
    expect(screen.getByText("One or more stored evidence records contradict this claim.")).toBeInTheDocument();
  });

  it("downloads a successful snapshot with the backend filename", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockImplementationOnce(() => response(queue)).mockImplementationOnce(() => response(snapshot, 200, { "content-disposition": "attachment; filename=\"verified-review-queue.json\"" }));
    vi.stubGlobal("fetch", fetchMock);
    const createObjectURL = vi.fn(() => "blob:snapshot");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
    let downloadedFilename = "";
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) { downloadedFilename = this.download; });
    render(<CrossInvestigationReviewQueuePanel />);
    await user.click(await screen.findByRole("button", { name: "Download queue snapshot" }));
    expect(downloadedFilename).toBe("verified-review-queue.json");
  });

  it("compares a valid prior snapshot and renders deterministic deltas", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn().mockImplementationOnce(() => response(queue)).mockImplementationOnce(() => response(comparison));
    vi.stubGlobal("fetch", fetchMock);
    render(<CrossInvestigationReviewQueuePanel />);
    await user.upload(await screen.findByLabelText("Prior snapshot JSON"), jsonFile(snapshot));
    await user.click(screen.getByRole("button", { name: "Compare snapshot" }));
    expect(await screen.findByLabelText("Snapshot comparison results")).toHaveTextContent("Added: 1");
    expect(screen.getByText(/blocked remediation: \+1/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith("/api/investigations/review-queue/snapshot/compare", expect.objectContaining({ method: "POST" }));
  });

  it("rejects malformed JSON before sending a comparison request", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(() => response(queue));
    vi.stubGlobal("fetch", fetchMock);
    render(<CrossInvestigationReviewQueuePanel />);
    await user.upload(await screen.findByLabelText("Prior snapshot JSON"), jsonFile("{", "bad.json"));
    await user.click(screen.getByRole("button", { name: "Compare snapshot" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("not valid JSON");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("shows backend digest mismatch without presenting comparison results", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn().mockImplementationOnce(() => response(queue)).mockImplementationOnce(() => response({ detail: "Snapshot digest does not match its canonical payload" }, 400)));
    render(<CrossInvestigationReviewQueuePanel />);
    await user.upload(await screen.findByLabelText("Prior snapshot JSON"), jsonFile(snapshot));
    await user.click(screen.getByRole("button", { name: "Compare snapshot" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("digest does not match");
    expect(screen.queryByLabelText("Snapshot comparison results")).not.toBeInTheDocument();
  });

  it("renders explicit empty state", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({ ...queue, status: "empty", item_count: 0, items: [] })));
    render(<CrossInvestigationReviewQueuePanel />);
    expect(await screen.findByText(/No stored investigation items currently require human review/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Compare snapshot" })).toBeDisabled();
  });

  it("renders failure and retry states", async () => {
    const user = userEvent.setup();
    let calls = 0;
    vi.stubGlobal("fetch", vi.fn(() => { calls += 1; return calls === 1 ? response({}, 503) : response({ ...queue, status: "empty", item_count: 0, items: [] }); }));
    render(<CrossInvestigationReviewQueuePanel />);
    await user.click(await screen.findByRole("button", { name: "Retry review queue" }));
    expect(await screen.findByText(/No stored investigation items currently require human review/)).toBeInTheDocument();
  });
});