import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PersonalMemoryEvidenceRemediationVerification } from "@/components/personal-memory-evidence-remediation-verification";

function response(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

const inventory = { items: [{ memory_id: 11, summary: "Verified intervention record" }] };
const verification = {
  memory_id: 11,
  project_id: 7,
  total_actions: 2,
  ready_for_resolution_count: 1,
  actions: [
    {
      action_key: "memory-remediation-ready",
      action_type: "add_direct_support",
      follow_up_id: 44,
      follow_up_status: "open",
      status: "ready_for_resolution",
      passed_count: 2,
      total_count: 2,
      criteria: [
        { criterion: "Supporting evidence exists.", passed: true, explanation: "Approved evidence is linked.", supporting_evidence_ids: [3] },
        { criterion: "Support is direct.", passed: true, explanation: "Claim and excerpt address the record.", supporting_evidence_ids: [3] },
      ],
    },
    {
      action_key: "memory-remediation-blocked",
      action_type: "review_evidence",
      follow_up_id: 45,
      follow_up_status: "open",
      status: "partially_satisfied",
      passed_count: 1,
      total_count: 2,
      criteria: [
        { criterion: "Statuses are final.", passed: true, explanation: "Statuses are final.", supporting_evidence_ids: [3] },
        { criterion: "Reviewer notes exist.", passed: false, explanation: "Reviewer notes are missing.", supporting_evidence_ids: [] },
      ],
    },
  ],
};

function addInventoryButton(text: string) {
  let existingInventory = document.querySelector('[aria-label="Personal memory inventory"]');
  if (!existingInventory) {
    existingInventory = document.createElement("div");
    existingInventory.setAttribute("aria-label", "Personal memory inventory");
    document.body.append(existingInventory);
  }
  const recordButton = document.createElement("button");
  recordButton.textContent = text;
  existingInventory.append(recordButton);
  return recordButton;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("PersonalMemoryEvidenceRemediationVerification", () => {
  it("shows criterion results and resolves only a ready follow-up with notes", async () => {
    const fetchMock = vi.fn((url: string, _options?: RequestInit) => {
      if (url === "/api/personal-memory/evidence-health") return response(inventory);
      if (url.endsWith("/verification/resolve")) return response({ resolved: true, follow_up_id: 44, status: "resolved" });
      return response(verification);
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("confirm", vi.fn(() => true));

    const recordButton = addInventoryButton("Verified intervention record");

    render(<PersonalMemoryEvidenceRemediationVerification />);
    expect(fetchMock).not.toHaveBeenCalled();
    fireEvent.click(recordButton);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/personal-memory/evidence-health",
      expect.objectContaining({ cache: "no-store", signal: expect.any(AbortSignal) }),
    ));
    expect(await screen.findByLabelText("Evidence remediation verification actions")).toHaveTextContent("1/2 action(s) ready for resolution");
    expect(screen.getByText(/Approved evidence is linked/)).toBeInTheDocument();
    expect(screen.getByText(/Reviewer notes are missing/)).toBeInTheDocument();
    expect(screen.getByText("All criteria must pass before resolution.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Resolve verified follow-up" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Resolution notes are required.");

    fireEvent.change(screen.getByLabelText("Resolution notes for add_direct_support"), {
      target: { value: "Direct support was verified and linked." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Resolve verified follow-up" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/personal-memory/11/evidence-remediation/verification/resolve",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          action_key: "memory-remediation-ready",
          confirmed: true,
          resolution_notes: "Direct support was verified and linked.",
        }),
      }),
    ));
  });

  it("aborts the lazy inventory request when unmounted", async () => {
    const fetchMock = vi.fn((_url: string, options?: RequestInit) => new Promise((_resolve, reject) => {
      options?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    }));
    vi.stubGlobal("fetch", fetchMock);

    const recordButton = addInventoryButton("Verified intervention record");
    const { unmount } = render(<PersonalMemoryEvidenceRemediationVerification />);
    fireEvent.click(recordButton);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const signal = fetchMock.mock.calls[0]?.[1]?.signal as AbortSignal;
    expect(signal.aborted).toBe(false);

    unmount();
    expect(signal.aborted).toBe(true);
  });

  it("aborts the prior verification request before loading a replacement selection", async () => {
    const replacementInventory = {
      items: [
        { memory_id: 11, summary: "Verified intervention record" },
        { memory_id: 12, summary: "Replacement verified record" },
      ],
    };
    const fetchMock = vi.fn((url: string, options?: RequestInit) => {
      if (url === "/api/personal-memory/evidence-health") return response(replacementInventory);
      return new Promise((_resolve, reject) => {
        options?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const firstButton = addInventoryButton("Verified intervention record");
    const secondButton = addInventoryButton("Replacement verified record");
    render(<PersonalMemoryEvidenceRemediationVerification />);

    fireEvent.click(firstButton);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const firstSignal = fetchMock.mock.calls[1]?.[1]?.signal as AbortSignal;
    expect(firstSignal.aborted).toBe(false);

    fireEvent.click(secondButton);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    const secondSignal = fetchMock.mock.calls[2]?.[1]?.signal as AbortSignal;

    expect(firstSignal.aborted).toBe(true);
    expect(secondSignal.aborted).toBe(false);
    expect(fetchMock.mock.calls[2]?.[0]).toBe("/api/personal-memory/12/evidence-remediation/verification");
  });
});
