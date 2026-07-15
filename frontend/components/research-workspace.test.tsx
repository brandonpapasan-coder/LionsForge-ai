import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchWorkspace } from "@/components/research-workspace";
import type { ResearchProject, ResearchSession } from "@/lib/research";

vi.mock("@/components/research-notebook-editor", () => ({
  ResearchNotebookEditor: () => <div>Research notebook</div>,
}));

const projects: ResearchProject[] = [
  {
    id: 1,
    title: "Grid Storage Study",
    description: null,
    objective: "Validate long-duration storage evidence.",
    status: "active",
    context: {},
    created_at: "2026-07-15T12:00:00Z",
    updated_at: "2026-07-15T12:00:00Z",
  },
  {
    id: 2,
    title: "Advanced Materials Study",
    description: null,
    objective: "Compare structural material claims.",
    status: "active",
    context: {},
    created_at: "2026-07-15T12:00:00Z",
    updated_at: "2026-07-15T12:00:00Z",
  },
];

const firstSessions: ResearchSession[] = [
  {
    id: 11,
    project_id: 1,
    title: "Stale grid session",
    objective: null,
    summary: null,
    status: "active",
    context: {},
    created_at: "2026-07-15T12:00:00Z",
    updated_at: "2026-07-15T12:00:00Z",
  },
];

const secondSessions: ResearchSession[] = [
  {
    id: 21,
    project_id: 2,
    title: "Current materials session",
    objective: null,
    summary: null,
    status: "active",
    context: {},
    created_at: "2026-07-15T12:00:00Z",
    updated_at: "2026-07-15T12:00:00Z",
  },
];

function response(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("ResearchWorkspace request lifecycle", () => {
  it("keeps sessions from the newest selected project", async () => {
    const staleResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let staleSignal: AbortSignal | undefined;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/research-projects") return response(projects);
      if (url === "/api/research-projects/1/sessions") {
        staleSignal = init?.signal ?? undefined;
        return staleResponse.promise;
      }
      if (url === "/api/research-projects/2/sessions") return response(secondSessions);
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ResearchWorkspace />);
    fireEvent.click(await screen.findByRole("button", { name: /Advanced Materials Study/i }));

    expect(await screen.findAllByText("Current materials session")).toHaveLength(2);
    expect(staleSignal?.aborted).toBe(true);

    staleResponse.resolve(await response(firstSessions));
    await waitFor(() => expect(screen.queryByText("Stale grid session")).not.toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "Advanced Materials Study" })).toBeInTheDocument();
  });

  it("aborts session creation when the selected project changes", async () => {
    const staleCreateResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let staleCreateSignal: AbortSignal | undefined;
    const staleCreatedSession: ResearchSession = {
      id: 12,
      project_id: 1,
      title: "Late grid experiment",
      objective: null,
      summary: null,
      status: "active",
      context: {},
      created_at: "2026-07-15T12:00:00Z",
      updated_at: "2026-07-15T12:00:00Z",
    };
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/research-projects") return response(projects);
      if (url === "/api/research-projects/1/sessions" && init?.method === "POST") {
        staleCreateSignal = init.signal ?? undefined;
        return staleCreateResponse.promise;
      }
      if (url === "/api/research-projects/1/sessions") return response([]);
      if (url === "/api/research-projects/2/sessions") return response(secondSessions);
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ResearchWorkspace />);
    await screen.findByRole("heading", { name: "Grid Storage Study" });
    fireEvent.change(screen.getByRole("textbox", { name: "Session title" }), {
      target: { value: "Late grid experiment" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Create session" }).closest("form")!);
    await waitFor(() => expect(staleCreateSignal).toBeDefined());

    fireEvent.click(screen.getByRole("button", { name: /Advanced Materials Study/i }));
    expect(staleCreateSignal?.aborted).toBe(true);
    expect(await screen.findAllByText("Current materials session")).toHaveLength(2);

    staleCreateResponse.resolve(await response(staleCreatedSession));
    await waitFor(() => expect(screen.queryByText("Late grid experiment")).not.toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "Advanced Materials Study" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create session" })).toBeEnabled();
  });

  it("aborts project discovery when unmounted", async () => {
    const projectResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let projectSignal: AbortSignal | undefined;
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      projectSignal = init?.signal ?? undefined;
      return projectResponse.promise;
    });
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<ResearchWorkspace />);
    await waitFor(() => expect(projectSignal).toBeDefined());
    unmount();

    expect(projectSignal?.aborted).toBe(true);
  });
});
