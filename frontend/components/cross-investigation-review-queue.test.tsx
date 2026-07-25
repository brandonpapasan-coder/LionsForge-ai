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

const snapshot = {
  artifact_type: "cross_investigation_review_queue_snapshot",
  queue,
  content_sha256: "abc123",
};

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("CrossInvestigationReviewQueuePanel", () => {
  it("renders stored provenance, filters, and investigation navigation", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", vi.fn(() => response(queue)));
    render(<CrossInvestigationReviewQueuePanel />);

    expect(await screen.findByText("Stored remediation progress is blocked.")).toBeInTheDocument();
    expect(screen.getByText(/not validation evidence or advice/)).toBeInTheDocument();
    expect(screen.getByText(/remediation_progress record 4/)).toBeInTheDocument();
    expect(screen.getByText(/digest verifies export integrity only/)).toBeInTheDocument();
    const navigationLinks = screen.getAllByRole("link", { name: "Open investigation context" });
    expect(navigationLinks).toHaveLength(3);
    expect(navigationLinks[0]).toHaveAttribute("href", "#investigation-7");

    await user.selectOptions(screen.getByLabelText("Review reason"), "unresolved_contradiction");
    expect(screen.getByText("One or more stored evidence records contradict this claim.")).toBeInTheDocument();
    expect(screen.queryByText("Stored remediation progress is blocked.")).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Review reason"), "all");
    await user.selectOptions(screen.getByLabelText("Investigation"), "9");
    expect(screen.getByText("Beta claim")).toBeInTheDocument();
    expect(screen.queryByText("Alpha claim")).not.toBeInTheDocument();
  });

  it("downloads a successful snapshot with the backend filename", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn()
      .mockImplementationOnce(() => response(queue))
      .mockImplementationOnce(() => response(snapshot, 200, {
        "content-disposition": "attachment; filename=\"verified-review-queue.json\"",
      }));
    vi.stubGlobal("fetch", fetchMock);
    const createObjectURL = vi.fn(() => "blob:snapshot");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
    let downloadedFilename = "";
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function () {
      downloadedFilename = this.download;
    });

    render(<CrossInvestigationReviewQueuePanel />);
    await user.click(await screen.findByRole("button", { name: "Download queue snapshot" }));

    expect(fetchMock).toHaveBeenLastCalledWith("/api/investigations/review-queue/snapshot", { cache: "no-store" });
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(downloadedFilename).toBe("verified-review-queue.json");
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:snapshot");
  });

  it("does not create a download when snapshot export fails", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn()
      .mockImplementationOnce(() => response(queue))
      .mockImplementationOnce(() => response({}, 503));
    vi.stubGlobal("fetch", fetchMock);
    const createObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL: vi.fn() });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click");

    render(<CrossInvestigationReviewQueuePanel />);
    await user.click(await screen.findByRole("button", { name: "Download queue snapshot" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No file was downloaded");
    expect(createObjectURL).not.toHaveBeenCalled();
    expect(click).not.toHaveBeenCalled();
  });

  it("renders explicit empty state", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response({ ...queue, status: "empty", item_count: 0, items: [] })));
    render(<CrossInvestigationReviewQueuePanel />);
    expect(await screen.findByText(/No stored investigation items currently require human review/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Download queue snapshot" })).toBeEnabled();
  });

  it("renders failure and retry states", async () => {
    const user = userEvent.setup();
    let calls = 0;
    vi.stubGlobal("fetch", vi.fn(() => {
      calls += 1;
      return calls === 1 ? response({}, 503) : response({ ...queue, status: "empty", item_count: 0, items: [] });
    }));
    render(<CrossInvestigationReviewQueuePanel />);
    await user.click(await screen.findByRole("button", { name: "Retry review queue" }));
    expect(await screen.findByText(/No stored investigation items currently require human review/)).toBeInTheDocument();
  });
});
