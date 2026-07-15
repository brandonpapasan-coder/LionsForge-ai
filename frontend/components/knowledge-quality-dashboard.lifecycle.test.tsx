import React from "react";
import { render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { KnowledgeQualityDashboard } from "@/components/knowledge-quality-dashboard";

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

describe("KnowledgeQualityDashboard mounted-state ownership", () => {
  it("ignores a late dashboard error response after unmount", async () => {
    const dashboardResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let dashboardSignal: AbortSignal | undefined;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/research-projects") return response([]);
      if (url === "/api/knowledge-quality") {
        dashboardSignal = init?.signal ?? undefined;
        return dashboardResponse.promise;
      }
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const { unmount } = render(<KnowledgeQualityDashboard />);
    await waitFor(() => expect(dashboardSignal).toBeDefined());

    unmount();
    expect(dashboardSignal?.aborted).toBe(true);

    dashboardResponse.resolve(await response(null, 404));
    await Promise.resolve();
    await Promise.resolve();

    expect(consoleError).not.toHaveBeenCalled();
  });

  it("does not start organization loading after project discovery is aborted", async () => {
    const projectsResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let projectsSignal: AbortSignal | undefined;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/research-projects") {
        projectsSignal = init?.signal ?? undefined;
        return projectsResponse.promise;
      }
      return response(null, 500);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<KnowledgeQualityDashboard />);
    await waitFor(() => expect(projectsSignal).toBeDefined());
    unmount();

    projectsResponse.resolve(await response([]));
    await Promise.resolve();
    await Promise.resolve();

    expect(projectsSignal?.aborted).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
