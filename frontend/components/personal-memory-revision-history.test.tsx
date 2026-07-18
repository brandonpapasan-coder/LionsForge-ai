import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PersonalMemoryControlCenter } from "@/components/personal-memory-control-center";

const summary = {
  project_id: null,
  total_count: 2,
  active_count: 2,
  archived_count: 0,
  user_authored_count: 2,
  research_generated_count: 0,
  revision_count: 4,
  by_status: { provisional: 2 },
  by_category: { learning_goal: 2 },
  available_controls: ["inspect", "revise", "recover_version", "archive", "restore", "delete"],
};

const memoryWithHistory = {
  id: 11,
  project_id: 7,
  statement: "Use primary evidence before commentary.",
  summary: "Prioritize primary evidence",
  category: "learning_goal",
  status: "provisional",
  confidence: 0.8,
  revision_number: 3,
  updated_at: "2026-07-18T12:00:00Z",
  revisions: [
    {
      id: 101,
      revision_number: 1,
      statement: "Use reliable evidence.",
      summary: "Prefer reliable evidence",
      category: "learning_goal",
      status: "provisional",
      confidence: 0.5,
      created_at: "2026-07-16T12:00:00Z",
    },
    {
      id: 102,
      revision_number: 2,
      statement: "Use original evidence before summaries.",
      summary: "Prefer original evidence",
      category: "learning_goal",
      status: "validated",
      confidence: 0.7,
      created_at: "2026-07-17T12:00:00Z",
    },
  ],
};

const memoryWithoutHistory = {
  id: 12,
  project_id: 8,
  statement: "Use concise explanations.",
  summary: "Prefer concise explanations",
  category: "mentor_preference",
  status: "provisional",
  confidence: 0.7,
  revision_number: 1,
  updated_at: "2026-07-18T12:00:00Z",
  revisions: [],
};

function response(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

function installFetch() {
  vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/personal-memory/summary") return response(summary);
    if (url === "/api/personal-memory") return response([memoryWithHistory, memoryWithoutHistory]);
    return response(null, 404);
  }));
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("PersonalMemoryControlCenter revision history", () => {
  it("shows the current record and prior revisions newest first", async () => {
    installFetch();
    render(<PersonalMemoryControlCenter />);

    const inventory = await screen.findByLabelText("Personal memory inventory");
    fireEvent.click(within(inventory).getByRole("button", { name: /Prioritize primary evidence/i }));
    fireEvent.click(screen.getByRole("button", { name: "View revision history" }));

    const history = screen.getByLabelText("Record revision history");
    expect(within(history).getByLabelText("Current revision 3")).toBeInTheDocument();
    const prior = within(history).getAllByLabelText(/Prior revision/);
    expect(prior).toHaveLength(2);
    expect(prior[0]).toHaveAccessibleName("Prior revision 2");
    expect(prior[1]).toHaveAccessibleName("Prior revision 1");
    expect(within(history).getByText("Prefer original evidence")).toBeInTheDocument();
  });

  it("shows an empty-history message and resets expansion when selection changes", async () => {
    installFetch();
    render(<PersonalMemoryControlCenter />);

    const inventory = await screen.findByLabelText("Personal memory inventory");
    fireEvent.click(within(inventory).getByRole("button", { name: /Prioritize primary evidence/i }));
    fireEvent.click(screen.getByRole("button", { name: "View revision history" }));
    expect(screen.getByLabelText("Record revision history")).toBeInTheDocument();

    fireEvent.click(within(inventory).getByRole("button", { name: /Prefer concise explanations/i }));
    expect(screen.queryByLabelText("Record revision history")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "View revision history" }));
    expect(screen.getByText("No prior revisions are available.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Hide revision history" })).toHaveAttribute("aria-expanded", "true");
  });

  it("recovers an earlier version as a new revision and refreshes the dashboard", async () => {
    let current = memoryWithHistory;
    let currentSummary = summary;
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/personal-memory/summary") return response(currentSummary);
      if (url === "/api/personal-memory") return response([current, memoryWithoutHistory]);
      if (url === "/api/personal-memory/11/recover/101" && init?.method === "POST") {
        current = {
          ...memoryWithHistory,
          statement: "Use reliable evidence.",
          summary: "Prefer reliable evidence",
          confidence: 0.5,
          revision_number: 4,
          revisions: [
            ...memoryWithHistory.revisions,
            {
              id: 103,
              revision_number: 3,
              statement: memoryWithHistory.statement,
              summary: memoryWithHistory.summary,
              category: memoryWithHistory.category,
              status: memoryWithHistory.status,
              confidence: memoryWithHistory.confidence,
              created_at: memoryWithHistory.updated_at,
            },
          ],
        };
        currentSummary = { ...summary, revision_count: 5 };
        return response(current);
      }
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<PersonalMemoryControlCenter />);
    const inventory = await screen.findByLabelText("Personal memory inventory");
    fireEvent.click(within(inventory).getByRole("button", { name: /Prioritize primary evidence/i }));
    fireEvent.click(screen.getByRole("button", { name: "View revision history" }));
    fireEvent.click(screen.getByRole("button", { name: "Recover revision 1" }));

    expect(confirm).toHaveBeenCalledWith(
      "Recover revision 1 as a new current revision? Later history will be preserved.",
    );
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/personal-memory/11/recover/101",
      { method: "POST", cache: "no-store" },
    ));
    await waitFor(() => expect(screen.getByLabelText("Current revision 4")).toBeInTheDocument());
    expect(screen.getAllByText("Prefer reliable evidence").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByLabelText("Record revision history")).toBeInTheDocument();
  });
});
