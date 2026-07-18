import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PersonalMemoryControlCenter } from "@/components/personal-memory-control-center";

const baseSummary = {
  project_id: null,
  total_count: 1,
  active_count: 1,
  archived_count: 0,
  user_authored_count: 1,
  research_generated_count: 0,
  revision_count: 1,
  by_status: { provisional: 1 },
  by_category: { learning_goal: 1 },
  available_controls: ["inspect", "revise", "archive", "restore", "delete"],
};

const memory = {
  id: 11,
  project_id: 7,
  statement: "Evaluate primary evidence before commentary.",
  summary: "Prioritize primary evidence",
  category: "learning_goal",
  status: "provisional",
  confidence: 0.7,
  revision_number: 1,
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

describe("PersonalMemoryControlCenter revision editor", () => {
  it("submits a revision and refreshes the selected record, inventory, and summary", async () => {
    let current = memory;
    let summary = baseSummary;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/personal-memory/summary") return response(summary);
      if (url === "/api/personal-memory") return response([current]);
      if (url === "/api/personal-memory/11" && init?.method === "PATCH") {
        expect(init.headers).toEqual({ "content-type": "application/json" });
        expect(JSON.parse(String(init.body))).toEqual({
          statement: "Evaluate original research before commentary.",
          summary: "Prioritize original research",
          category: "research_method",
          status: "validated",
          confidence: 0.9,
        });
        current = {
          ...memory,
          statement: "Evaluate original research before commentary.",
          summary: "Prioritize original research",
          category: "research_method",
          status: "validated",
          confidence: 0.9,
          revision_number: 2,
        };
        summary = { ...baseSummary, revision_count: 2 };
        return response(current);
      }
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<PersonalMemoryControlCenter />);
    const inventory = await screen.findByLabelText("Personal memory inventory");
    fireEvent.click(within(inventory).getByRole("button", { name: /Prioritize primary evidence/i }));
    fireEvent.click(screen.getByRole("button", { name: "Edit record" }));

    fireEvent.change(screen.getByLabelText("Revision summary"), {
      target: { value: "Prioritize original research" },
    });
    fireEvent.change(screen.getByLabelText("Revision statement"), {
      target: { value: "Evaluate original research before commentary." },
    });
    fireEvent.change(screen.getByLabelText("Revision category"), {
      target: { value: "research_method" },
    });
    fireEvent.change(screen.getByLabelText("Revision confidence"), {
      target: { value: "0.9" },
    });
    fireEvent.change(screen.getByLabelText("Revision status"), {
      target: { value: "validated" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save revision" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/personal-memory/11",
      expect.objectContaining({ method: "PATCH", cache: "no-store" }),
    ));
    await waitFor(() => expect(screen.getByText(/revision 2/i)).toBeInTheDocument());
    expect(screen.getAllByText("Prioritize original research").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([url]) => String(url) === "/api/personal-memory").length).toBeGreaterThanOrEqual(2);
    expect(fetchMock.mock.calls.filter(([url]) => String(url) === "/api/personal-memory/summary").length).toBeGreaterThanOrEqual(2);
  });

  it("shows backend validation details and keeps the editor open", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/personal-memory/summary") return response(baseSummary);
      if (url === "/api/personal-memory") return response([memory]);
      if (url === "/api/personal-memory/11" && init?.method === "PATCH") {
        return response({ detail: "Validated memory requires confidence of at least 0.5" }, 422);
      }
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<PersonalMemoryControlCenter />);
    const inventory = await screen.findByLabelText("Personal memory inventory");
    fireEvent.click(within(inventory).getByRole("button", { name: /Prioritize primary evidence/i }));
    fireEvent.click(screen.getByRole("button", { name: "Edit record" }));
    fireEvent.change(screen.getByLabelText("Revision status"), { target: { value: "validated" } });
    fireEvent.change(screen.getByLabelText("Revision confidence"), { target: { value: "0.2" } });
    fireEvent.click(screen.getByRole("button", { name: "Save revision" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Validated memory requires confidence of at least 0.5",
    );
    expect(screen.getByLabelText("Knowledge record revision editor")).toBeInTheDocument();
  });

  it("validates confidence locally before calling the revision endpoint", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/personal-memory/summary") return response(baseSummary);
      if (url === "/api/personal-memory") return response([memory]);
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<PersonalMemoryControlCenter />);
    const inventory = await screen.findByLabelText("Personal memory inventory");
    fireEvent.click(within(inventory).getByRole("button", { name: /Prioritize primary evidence/i }));
    fireEvent.click(screen.getByRole("button", { name: "Edit record" }));
    fireEvent.change(screen.getByLabelText("Revision confidence"), { target: { value: "1.5" } });
    fireEvent.click(screen.getByRole("button", { name: "Save revision" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Confidence must be a number from 0 to 1.");
    expect(fetchMock.mock.calls.some(([url, init]) => String(url) === "/api/personal-memory/11" && init?.method === "PATCH")).toBe(false);
  });
});
