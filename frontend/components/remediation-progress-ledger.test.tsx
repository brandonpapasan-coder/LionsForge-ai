import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RemediationProgressLedgerPanel } from "@/components/remediation-progress-ledger";

function response(body: unknown, status = 200) {
  return Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body });
}

const ledger = {
  contract_version: "1.0", investigation_id: 7, title: "Review", status: "active",
  generated_from: "user_progress_and_current_remediation_plan",
  interpretation_notice: "User-authored workflow records.",
  entries: [{
    claim_id: 1, claim_sequence: 1, statement: "The claim", status: "blocked", notes: "Need source",
    authorship: "user_authored", is_stale: true, stale_reasons: ["The priority changed."],
    action_type_snapshot: "resolve_contradiction", priority_snapshot: 1,
    plan_generated_at_snapshot: "2026-07-25T17:00:00Z",
    current_action: { action_type: "collect_direct_evidence", priority: 2, rationale: "Collect evidence.", completion_criteria: ["Attach direct evidence."], generated_from_stored_state_at: "2026-07-25T18:00:00Z" },
    created_at: "2026-07-25T17:00:00Z", updated_at: "2026-07-25T17:30:00Z",
  }],
};

const history = {
  contract_version: "1.0", investigation_id: 7, claim_id: 1, status: "active",
  generated_from: "append_only_user_progress_history",
  interpretation_notice: "Append-only user-authored workflow history.",
  events: [
    { event_id: 2, claim_id: 1, status: "blocked", notes: "Need source", authorship: "user_authored", action_type_snapshot: "resolve_contradiction", priority_snapshot: 1, plan_generated_at_snapshot: "2026-07-25T17:00:00Z", recorded_at: "2026-07-25T17:30:00Z" },
    { event_id: 1, claim_id: 1, status: "in_progress", notes: null, authorship: "user_authored", action_type_snapshot: "attach_initial_evidence", priority_snapshot: 2, plan_generated_at_snapshot: "2026-07-25T16:00:00Z", recorded_at: "2026-07-25T16:30:00Z" },
  ],
};

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("RemediationProgressLedgerPanel", () => {
  it("renders stale user-authored progress and saves an update", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn()
      .mockImplementationOnce(() => response(ledger))
      .mockImplementationOnce(() => response({ ...ledger, entries: [{ ...ledger.entries[0], status: "ready_for_review", is_stale: false, stale_reasons: [] }] }));
    vi.stubGlobal("fetch", fetchMock);
    render(<RemediationProgressLedgerPanel investigationId={7} />);
    expect(await screen.findByText("Progress record needs review")).toBeInTheDocument();
    expect(screen.getByText(/user authored/)).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Workflow status"), "ready_for_review");
    await user.click(screen.getByRole("button", { name: "Save progress" }));
    expect(fetchMock).toHaveBeenLastCalledWith("/api/investigations/7/remediation-progress/1", expect.objectContaining({ method: "PUT" }));
  });

  it("lazy loads and renders append-only progress history", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn()
      .mockImplementationOnce(() => response(ledger))
      .mockImplementationOnce(() => response(history));
    vi.stubGlobal("fetch", fetchMock);
    render(<RemediationProgressLedgerPanel investigationId={7} />);
    await screen.findByText("Progress record needs review");
    await user.click(screen.getByText("Progress history"));
    expect(await screen.findByRole("article", { name: "History event 2" })).toHaveTextContent("Need source");
    expect(screen.getByText("No researcher note recorded.")).toBeInTheDocument();
    expect(screen.getByText(/not validation evidence/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenLastCalledWith("/api/investigations/7/remediation-progress/1/history", { cache: "no-store" });
  });

  it("renders history failure and retry states", async () => {
    const user = userEvent.setup();
    let historyCalls = 0;
    vi.stubGlobal("fetch", vi.fn((url: string) => {
      if (url.endsWith("/history")) {
        historyCalls += 1;
        return historyCalls === 1 ? response({}, 503) : response({ ...history, status: "empty", events: [] });
      }
      return response(ledger);
    }));
    render(<RemediationProgressLedgerPanel investigationId={7} />);
    await screen.findByText("Progress record needs review");
    await user.click(screen.getByText("Progress history"));
    await user.click(await screen.findByRole("button", { name: "Retry progress history" }));
    expect(await screen.findByText(/No history events have been recorded/)).toBeInTheDocument();
  });

  it("renders empty and retry states", async () => {
    const user = userEvent.setup();
    let calls = 0;
    vi.stubGlobal("fetch", vi.fn(() => {
      calls += 1;
      return calls === 1 ? response({}, 503) : response({ ...ledger, status: "empty", entries: [] });
    }));
    render(<RemediationProgressLedgerPanel investigationId={7} />);
    await user.click(await screen.findByRole("button", { name: "Retry progress ledger" }));
    expect(await screen.findByText(/No remediation progress has been recorded/)).toBeInTheDocument();
  });
});
