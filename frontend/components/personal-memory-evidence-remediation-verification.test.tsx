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

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("PersonalMemoryEvidenceRemediationVerification", () => {
  it("shows criterion results and resolves only a ready follow-up with notes", async () => {
    const fetchMock = vi.fn((url: string) => {
      if (url === "/api/personal-memory/evidence-health") return response(inventory);
      if (url.endsWith("/verification/resolve")) return response({ resolved: true, follow_up_id: 44, status: "resolved" });
      return response(verification);
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("confirm", vi.fn(() => true));

    const existingInventory = document.createElement("div");
    existingInventory.setAttribute("aria-label", "Personal memory inventory");
    const recordButton = document.createElement("button");
    recordButton.textContent = "Verified intervention record";
    existingInventory.append(recordButton);
    document.body.append(existingInventory);

    render(<PersonalMemoryEvidenceRemediationVerification />);
    expect(fetchMock).not.toHaveBeenCalled();
    fireEvent.click(recordButton);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/personal-memory/evidence-health", { cache: "no-store" }));
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
});
