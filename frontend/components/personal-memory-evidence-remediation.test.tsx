import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PersonalMemoryEvidenceRemediation } from "@/components/personal-memory-evidence-remediation";

function response(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

const inventory = {
  items: [{ memory_id: 11, summary: "Contested intervention finding" }],
};

const plan = {
  memory_id: 11,
  project_id: 7,
  health: { classification: "contested" },
  total_actions: 1,
  open_follow_up_count: 0,
  actions: [
    {
      action_key: "memory-remediation-key",
      action_type: "resolve_contradiction",
      priority: "urgent",
      rationale: "The record has conflicting evidence.",
      action_text: "Review the conflict and document the preferred interpretation.",
      related_evidence_ids: [3, 4],
      completion_criteria: ["The contradiction is documented.", "The record reflects the resolved interpretation."],
      existing_follow_up_id: null,
    },
  ],
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("PersonalMemoryEvidenceRemediation", () => {
  it("loads the selected record plan and creates a confirmed research follow-up", async () => {
    const refreshed = {
      ...plan,
      open_follow_up_count: 1,
      actions: [{ ...plan.actions[0], existing_follow_up_id: 91 }],
    };
    let planLoads = 0;
    const fetchMock = vi.fn((input: string, init?: RequestInit) => {
      if (input === "/api/personal-memory/evidence-health") return response(inventory);
      if (input === "/api/personal-memory/11/evidence-remediation" && !init?.method) {
        planLoads += 1;
        return response(planLoads === 1 ? plan : refreshed);
      }
      if (input === "/api/personal-memory/11/evidence-remediation/follow-ups") {
        return response({ created: true, follow_up_id: 91, action_key: "memory-remediation-key" });
      }
      throw new Error(`Unexpected fetch ${input}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    const existingInventory = document.createElement("div");
    existingInventory.setAttribute("aria-label", "Personal memory inventory");
    const recordButton = document.createElement("button");
    recordButton.textContent = "Contested intervention finding";
    existingInventory.append(recordButton);
    document.body.append(existingInventory);

    render(<PersonalMemoryEvidenceRemediation />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/personal-memory/evidence-health",
      { cache: "no-store" },
    ));

    fireEvent.click(recordButton);

    expect(await screen.findByText("resolve contradiction")).toBeInTheDocument();
    expect(screen.getByText("The contradiction is documented.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Create research follow-up" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/personal-memory/11/evidence-remediation/follow-ups",
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ action_key: "memory-remediation-key", confirmed: true }),
        cache: "no-store",
      },
    ));
    expect(await screen.findByText("Follow-up #91 already open")).toBeInTheDocument();
  });

  it("does not create a follow-up when confirmation is declined", async () => {
    const fetchMock = vi.fn((input: string) => {
      if (input === "/api/personal-memory/evidence-health") return response(inventory);
      if (input === "/api/personal-memory/11/evidence-remediation") return response(plan);
      throw new Error(`Unexpected fetch ${input}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "confirm").mockReturnValue(false);

    const existingInventory = document.createElement("div");
    existingInventory.setAttribute("aria-label", "Personal memory inventory");
    const recordButton = document.createElement("button");
    recordButton.textContent = "Contested intervention finding";
    existingInventory.append(recordButton);
    document.body.append(existingInventory);

    render(<PersonalMemoryEvidenceRemediation />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    fireEvent.click(recordButton);
    fireEvent.click(await screen.findByRole("button", { name: "Create research follow-up" }));

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
