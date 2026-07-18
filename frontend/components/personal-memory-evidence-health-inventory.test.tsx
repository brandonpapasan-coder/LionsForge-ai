import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PersonalMemoryEvidenceHealthInventory } from "@/components/personal-memory-evidence-health-inventory";

function response(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

const inventory = {
  project_id: null,
  classification: null,
  total_count: 2,
  by_classification: { contested: 1, unsupported: 1 },
  items: [
    {
      memory_id: 11,
      project_id: 7,
      summary: "Contested intervention finding",
      statement: "Evidence disagrees about the intervention.",
      category: "research_context",
      status: "provisional",
      confidence: 0.7,
      updated_at: "2026-07-18T00:00:00",
      health: {
        classification: "contested",
        total_count: 2,
        available_count: 2,
        unavailable_count: 0,
        approved_count: 0,
        needs_review_count: 2,
        supporting_count: 1,
        contradicting_count: 1,
        average_credibility: 0.8,
        average_freshness: 0.7,
        average_confidence: 0.75,
        reasons: ["The linked evidence contains both supporting and contradicting claims."],
        recommended_actions: ["Review the contradiction and document why one interpretation is preferred."],
      },
    },
    {
      memory_id: 12,
      project_id: 7,
      summary: "Unsupported finding",
      statement: "No evidence is linked.",
      category: "research_context",
      status: "provisional",
      confidence: 0.5,
      updated_at: "2026-07-17T00:00:00",
      health: {
        classification: "unsupported",
        total_count: 0,
        available_count: 0,
        unavailable_count: 0,
        approved_count: 0,
        needs_review_count: 0,
        supporting_count: 0,
        contradicting_count: 0,
        average_credibility: null,
        average_freshness: null,
        average_confidence: null,
        reasons: ["This saved record has no linked evidence."],
        recommended_actions: ["Link at least one relevant source before relying on this record."],
      },
    },
  ],
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  document.body.innerHTML = "";
});

describe("PersonalMemoryEvidenceHealthInventory", () => {
  it("shows weakest-first records, aggregate counts, and opens the matching saved record", async () => {
    const fetchMock = vi.fn(() => response(inventory));
    vi.stubGlobal("fetch", fetchMock);
    const click = vi.fn();
    const scrollIntoView = vi.fn();
    Element.prototype.scrollIntoView = scrollIntoView;

    const existingInventory = document.createElement("div");
    existingInventory.setAttribute("aria-label", "Personal memory inventory");
    const recordButton = document.createElement("button");
    recordButton.textContent = "Contested intervention finding";
    recordButton.addEventListener("click", click);
    existingInventory.append(recordButton);
    const selected = document.createElement("article");
    selected.setAttribute("aria-label", "Selected memory");
    document.body.append(existingInventory, selected);

    render(<PersonalMemoryEvidenceHealthInventory />);

    const panel = await screen.findByLabelText("Evidence health inventory");
    const buttons = within(panel).getAllByRole("button");
    expect(buttons[0]).toHaveTextContent("Contested intervention finding");
    expect(screen.getByLabelText("Evidence health classification counts")).toHaveTextContent("contested1");

    fireEvent.click(buttons[0]);
    expect(click).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(scrollIntoView).toHaveBeenCalled());
  });

  it("forwards project and classification filters", async () => {
    const fetchMock = vi.fn(() => response(inventory));
    vi.stubGlobal("fetch", fetchMock);

    render(<PersonalMemoryEvidenceHealthInventory />);
    await screen.findByLabelText("Evidence health inventory");
    fireEvent.change(screen.getByLabelText("Evidence health project ID"), { target: { value: "7" } });
    fireEvent.change(screen.getByLabelText("Evidence health classification"), { target: { value: "weak" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply triage filters" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/personal-memory/evidence-health?project_id=7&classification=weak",
      { cache: "no-store" },
    ));
  });
});
