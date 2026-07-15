import React from "react";
import { render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchWorkspace } from "@/components/research-workspace";

vi.mock("@/components/research-notebook-editor", () => ({
  ResearchNotebookEditor: () => <div>Research notebook</div>,
}));

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

describe("ResearchWorkspace mounted-state ownership", () => {
  it("ignores a late unauthorized project response after unmount", async () => {
    const projectResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let projectSignal: AbortSignal | undefined;
    const location = { href: "http://localhost/research" };

    vi.stubGlobal("location", location);
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      projectSignal = init?.signal ?? undefined;
      return projectResponse.promise;
    }));

    const view = render(<ResearchWorkspace />);
    await waitFor(() => expect(projectSignal).toBeDefined());
    view.unmount();

    expect(projectSignal?.aborted).toBe(true);
    projectResponse.resolve(await response(null, 401));

    await waitFor(() => expect(location.href).toBe("http://localhost/research"));
  });
});
