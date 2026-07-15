import React from "react";
import { render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EducationHub } from "@/components/education-hub";

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

describe("EducationHub mounted-state ownership", () => {
  it("does not redirect when an unauthorized load response resolves after unmount", async () => {
    const loadResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let loadSignal: AbortSignal | undefined;
    const originalLocation = window.location;
    const location = { href: "http://localhost/education" };

    Object.defineProperty(window, "location", {
      configurable: true,
      value: location,
    });

    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      loadSignal = init?.signal ?? undefined;
      return loadResponse.promise;
    }));

    const view = render(<EducationHub />);
    await waitFor(() => expect(loadSignal).toBeDefined());
    view.unmount();

    expect(loadSignal?.aborted).toBe(true);
    loadResponse.resolve(await response(null, 401));
    await Promise.resolve();

    expect(location.href).toBe("http://localhost/education");

    Object.defineProperty(window, "location", {
      configurable: true,
      value: originalLocation,
    });
  });
});
