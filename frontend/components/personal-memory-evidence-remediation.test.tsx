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
  items: [
    { memory_id: 11, summary: "Contested intervention finding" },
    { memory_id: 12, summary: "Weak replication finding" },
  ],
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

function appendInventoryButtons() {
  const existingInventory = document.createElement("div");
  existingInventory.setAttribute("aria-label", "Personal memory inventory");
  const firstButton = document.createElement("button");
  firstButton.textContent = "Contested intervention finding";
  const secondButton = document.createElement("button");
  secondButton.textContent = "Weak replication finding";
  existingInventory.append(firstButton, secondButton);
  document.body.append(existingInventory);
  return { firstButton, secondButton };
}

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

    const { firstButton } = appendInventoryButtons();
    render(<PersonalMemoryEvidenceRemediation />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/personal-memory/evidence-health",
      expect.objectContaining({ cache: "no-store", signal: expect.any(AbortSignal) }),
    ));

    fireEvent.click(firstButton);

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

    const { firstButton } = appendInventoryButtons();
    render(<PersonalMemoryEvidenceRemediation />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    fireEvent.click(firstButton);
    fireEvent.click(await screen.findByRole("button", { name: "Create research follow-up" }));

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("aborts inventory and plan requests when unmounted", async () => {
    const fetchMock = vi.fn((input: string, init?: RequestInit) => {
      if (input === "/api/personal-memory/evidence-health") return response(inventory);
      return new Promise((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const { firstButton } = appendInventoryButtons();
    const { unmount } = render(<PersonalMemoryEvidenceRemediation />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const inventorySignal = fetchMock.mock.calls[0]?.[1]?.signal as AbortSignal;
    fireEvent.click(firstButton);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const planSignal = fetchMock.mock.calls[1]?.[1]?.signal as AbortSignal;

    unmount();

    expect(inventorySignal.aborted).toBe(true);
    expect(planSignal.aborted).toBe(true);
  });

  it("aborts the prior plan request before loading a replacement selection", async () => {
    const fetchMock = vi.fn((input: string, init?: RequestInit) => {
      if (input === "/api/personal-memory/evidence-health") return response(inventory);
      return new Promise((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const { firstButton, secondButton } = appendInventoryButtons();
    render(<PersonalMemoryEvidenceRemediation />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    fireEvent.click(firstButton);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    const firstPlanSignal = fetchMock.mock.calls[1]?.[1]?.signal as AbortSignal;

    fireEvent.click(secondButton);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));

    expect(firstPlanSignal.aborted).toBe(true);
    expect(fetchMock.mock.calls[2]?.[0]).toBe("/api/personal-memory/12/evidence-remediation");
    expect((fetchMock.mock.calls[2]?.[1]?.signal as AbortSignal).aborted).toBe(false);
  });
});
