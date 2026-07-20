import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PersonalMemoryEvidenceRemediationEscalations } from "@/components/personal-memory-evidence-remediation-escalations";

function response(body: unknown, status = 200) {
  return Promise.resolve({ ok: status >= 200 && status < 300, status, json: async () => body });
}

const inventory = {
  project_id: null,
  escalation_state: null,
  total: 2,
  by_state: { fresh: 0, aging: 0, overdue: 1, critical: 1 },
  items: [
    {
      follow_up_id: 9,
      project_id: 7,
      evidence_id: 0,
      action_key: "critical-key",
      governing_rule: "saved_record_add_direct_support",
      status: "open",
      priority: "urgent",
      escalation_state: "critical",
      age_days: 5,
      idle_days: 5,
      due_at: null,
      days_overdue: 0,
      next_escalation_at: null,
      escalation_reason: "The urgent follow-up has remained active for 5 day(s).",
      recommended_owner_action: "Review immediately.",
    },
    {
      follow_up_id: 10,
      project_id: 7,
      evidence_id: 0,
      action_key: "overdue-key",
      governing_rule: "saved_record_review_evidence",
      status: "blocked",
      priority: "high",
      escalation_state: "overdue",
      age_days: 6,
      idle_days: 3,
      due_at: null,
      days_overdue: 0,
      next_escalation_at: "2026-07-20T00:00:00",
      escalation_reason: "The high follow-up exceeded its deterministic review window.",
      recommended_owner_action: "Review today.",
    },
  ],
  disclaimer: "Escalation states prioritize owner review only.",
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("PersonalMemoryEvidenceRemediationEscalations", () => {
  it("shows critical-first escalation details and applies filters with a replaceable request signal", async () => {
    const fetchMock = vi.fn(() => response(inventory));
    vi.stubGlobal("fetch", fetchMock);

    render(<PersonalMemoryEvidenceRemediationEscalations />);

    const list = await screen.findByLabelText("Evidence remediation escalation inventory");
    expect(list).toHaveTextContent("Follow-up #9");
    expect(list).toHaveTextContent("Review immediately");
    expect(screen.getByLabelText("Evidence remediation escalation metrics")).toHaveTextContent("critical1");

    const initialSignal = fetchMock.mock.calls[0]?.[1]?.signal as AbortSignal;
    fireEvent.change(screen.getByLabelText("Escalation project ID"), { target: { value: "7" } });
    fireEvent.change(screen.getByLabelText("Escalation state"), { target: { value: "critical" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const filteredSignal = fetchMock.mock.calls[1]?.[1]?.signal as AbortSignal;
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      "/api/personal-memory/evidence-remediation/escalations?project_id=7&escalation_state=critical",
    );
    expect(fetchMock.mock.calls[1]?.[1]?.cache).toBe("no-store");
    expect(initialSignal.aborted).toBe(false);
    expect(filteredSignal).not.toBe(initialSignal);
  });

  it("aborts the active escalation request when unmounted", () => {
    const fetchMock = vi.fn((_url: string, options?: RequestInit) => new Promise((_resolve, reject) => {
      options?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    }));
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<PersonalMemoryEvidenceRemediationEscalations />);
    const signal = fetchMock.mock.calls[0]?.[1]?.signal as AbortSignal;

    expect(signal.aborted).toBe(false);
    unmount();
    expect(signal.aborted).toBe(true);
  });

  it("aborts the prior in-flight request before applying replacement filters", async () => {
    const fetchMock = vi.fn((_url: string, options?: RequestInit) => new Promise((_resolve, reject) => {
      options?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    }));
    vi.stubGlobal("fetch", fetchMock);

    render(<PersonalMemoryEvidenceRemediationEscalations />);
    const initialSignal = fetchMock.mock.calls[0]?.[1]?.signal as AbortSignal;

    fireEvent.change(screen.getByLabelText("Escalation project ID"), { target: { value: "7" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(initialSignal.aborted).toBe(true);
    expect((fetchMock.mock.calls[1]?.[1]?.signal as AbortSignal).aborted).toBe(false);
  });
});
