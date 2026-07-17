import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { GET } from "@/app/api/mentor/conversations/route";

describe("mentor conversations API route", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    getCookie.mockReset();
  });

  it("returns 401 without a session and does not call the backend", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const response = await GET();

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ detail: "Not authenticated" });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("forwards authentication, disables caching, and preserves the upstream response", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([{ id: "conversation-1" }]), {
        status: 206,
        headers: { "content-type": "application/json" },
      }),
    );

    const response = await GET();

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/mentor/conversations",
      {
        headers: { authorization: "Bearer session-token" },
        cache: "no-store",
      },
    );
    expect(response.status).toBe(206);
    await expect(response.json()).resolves.toEqual([{ id: "conversation-1" }]);
  });

  it("returns a stable non-sensitive 503 when the backend connection fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new Error("connect ECONNREFUSED http://internal-backend:8000"),
    );

    const response = await GET();
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Mentor conversation service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("internal-backend");
    expect(JSON.stringify(body)).not.toContain("ECONNREFUSED");
  });

  it("returns the same stable 503 when reading the upstream body fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      text: vi.fn().mockRejectedValue(new Error("upstream stream failed")),
    } as unknown as Response);

    const response = await GET();

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Mentor conversation service is unavailable",
    });
  });
});
