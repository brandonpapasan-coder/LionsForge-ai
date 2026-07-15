import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import LoginPage from "@/app/login/page";

const push = vi.fn();
const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
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
  push.mockReset();
  refresh.mockReset();
});

describe("LoginPage request lifecycle", () => {
  it("navigates after the active login request succeeds", async () => {
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      expect(init).toEqual(expect.objectContaining({
        method: "POST",
        signal: expect.any(AbortSignal),
      }));
      return response({ ok: true });
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "brandon@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/mentor"));
    expect(refresh).toHaveBeenCalledTimes(1);
  });

  it("makes the newest submission authoritative", async () => {
    const first = deferred<Awaited<ReturnType<typeof response>>>();
    const second = deferred<Awaited<ReturnType<typeof response>>>();
    const signals: AbortSignal[] = [];
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      signals.push(init?.signal as AbortSignal);
      return signals.length === 1 ? first.promise : second.promise;
    });
    vi.stubGlobal("fetch", fetchMock);

    const { container } = render(<LoginPage />);
    const form = container.querySelector("form");
    expect(form).not.toBeNull();
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "brandon@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret" } });
    fireEvent.submit(form!);
    fireEvent.submit(form!);

    await waitFor(() => expect(signals).toHaveLength(2));
    expect(signals[0].aborted).toBe(true);

    first.resolve(await response({ detail: "Old failure" }, 401));
    second.resolve(await response({ ok: true }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/mentor"));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(push).toHaveBeenCalledTimes(1);
  });

  it("aborts login when unmounted", async () => {
    const loginResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let loginSignal: AbortSignal | undefined;
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      loginSignal = init?.signal ?? undefined;
      return loginResponse.promise;
    });
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "brandon@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(loginSignal).toBeDefined());

    unmount();

    expect(loginSignal?.aborted).toBe(true);
  });
});
