import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchNotebookEditor } from "@/components/research-notebook-editor";
import type { ResearchProject } from "@/lib/research";

const firstProject: ResearchProject = {
  id: 1,
  title: "Grid Storage Study",
  description: null,
  objective: "Validate storage evidence.",
  status: "active",
  context: { notebook: { thesis: "Initial grid thesis" } },
  created_at: "2026-07-15T12:00:00Z",
  updated_at: "2026-07-15T12:00:00Z",
};

const secondProject: ResearchProject = {
  id: 2,
  title: "Advanced Materials Study",
  description: null,
  objective: "Compare material claims.",
  status: "active",
  context: { notebook: { thesis: "Current materials thesis" } },
  created_at: "2026-07-15T12:00:00Z",
  updated_at: "2026-07-15T12:00:00Z",
};

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

describe("ResearchNotebookEditor request lifecycle", () => {
  it("does not apply a stale save after switching projects", async () => {
    const saveResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let saveSignal: AbortSignal | undefined;
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      saveSignal = init?.signal ?? undefined;
      return saveResponse.promise;
    });
    const onSaved = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const { rerender } = render(<ResearchNotebookEditor project={firstProject} onSaved={onSaved} />);
    fireEvent.change(screen.getByLabelText("Thesis"), { target: { value: "Updated grid thesis" } });
    fireEvent.click(screen.getByRole("button", { name: "Save notebook" }));

    await waitFor(() => expect(saveSignal).toBeDefined());
    rerender(<ResearchNotebookEditor project={secondProject} onSaved={onSaved} />);

    expect(saveSignal?.aborted).toBe(true);
    expect(screen.getByLabelText("Thesis")).toHaveValue("Current materials thesis");

    saveResponse.resolve(await response({ ...firstProject, context: { notebook: { thesis: "Updated grid thesis" } } }));
    await waitFor(() => expect(onSaved).not.toHaveBeenCalled());
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("aborts an active save when unmounted", async () => {
    const saveResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let saveSignal: AbortSignal | undefined;
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      saveSignal = init?.signal ?? undefined;
      return saveResponse.promise;
    });
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<ResearchNotebookEditor project={firstProject} onSaved={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Save notebook" }));
    await waitFor(() => expect(saveSignal).toBeDefined());

    unmount();

    expect(saveSignal?.aborted).toBe(true);
  });
});
