import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PersonalMemoryControlCenter } from "@/components/personal-memory-control-center";

const summary = {
  project_id: null,
  total_count: 2,
  active_count: 1,
  archived_count: 1,
  user_authored_count: 1,
  research_generated_count: 1,
  revision_count: 3,
  by_status: { archived: 1, provisional: 1 },
  by_category: { learning_goal: 1, mentor_preference: 1 },
  available_controls: ["inspect", "archive", "restore", "delete"],
};

const activeMemory = {
  id: 11,
  project_id: 7,
  statement: "Evaluate primary evidence before commentary.",
  summary: "Prioritize primary evidence",
  category: "learning_goal",
  status: "provisional",
  confidence: 0.7,
  revision_number: 1,
};

const archivedMemory = {
  id: 12,
  project_id: 8,
  statement: "Use concise mentor explanations.",
  summary: "Prefer concise explanations",
  category: "mentor_preference",
  status: "archived",
  confidence: 0.8,
  revision_number: 2,
};

function response(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("PersonalMemoryControlCenter inventory", () => {
  it("loads a browsable inventory and applies encoded filters", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/personal-memory/summary") return response(summary);
      if (url === "/api/personal-memory") return response([activeMemory, archivedMemory]);
      if (url.includes("project_id=7") && url.includes("status=provisional") && url.includes("category=learning_goal") && url.includes("query=primary+sources")) {
        return response([activeMemory]);
      }
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<PersonalMemoryControlCenter />);

    expect(await screen.findByText("Prioritize primary evidence")).toBeInTheDocument();
    expect(screen.getByText("Prefer concise explanations")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Project ID"), { target: { value: "7" } });
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "provisional" } });
    fireEvent.change(screen.getByLabelText("Category"), { target: { value: "learning_goal" } });
    fireEvent.change(screen.getByLabelText("Search memories"), { target: { value: "primary sources" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/personal-memory?project_id=7&status=provisional&category=learning_goal&query=primary+sources",
        { cache: "no-store" },
      );
    });
    expect(screen.getByText("Prioritize primary evidence")).toBeInTheDocument();
    expect(screen.queryByText("Prefer concise explanations")).not.toBeInTheDocument();
  });

  it("selects an inventory item and refreshes inventory and summary after archive", async () => {
    let archived = false;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/personal-memory/summary") return response(summary);
      if (url === "/api/personal-memory") {
        return response([{ ...activeMemory, status: archived ? "archived" : "provisional" }]);
      }
      if (url === "/api/personal-memory/11/archive" && init?.method === "POST") {
        archived = true;
        return response({ ...activeMemory, status: "archived" });
      }
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<PersonalMemoryControlCenter />);
    const inventory = await screen.findByLabelText("Personal memory inventory");
    fireEvent.click(within(inventory).getByRole("button", { name: /Prioritize primary evidence/i }));
    expect(screen.getByLabelText("Selected memory")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Archive" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/personal-memory/11/archive",
        { method: "POST", cache: "no-store" },
      );
    });
    await waitFor(() => expect(screen.getByRole("button", { name: "Restore" })).toBeInTheDocument());
    expect(fetchMock.mock.calls.filter(([url]) => String(url) === "/api/personal-memory").length).toBeGreaterThanOrEqual(2);
    expect(fetchMock.mock.calls.filter(([url]) => String(url) === "/api/personal-memory/summary").length).toBeGreaterThanOrEqual(2);
  });
});
