import { beforeEach, describe, expect, it, vi } from "vitest";

const cookieGet = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: cookieGet })),
}));

import { GET } from "@/app/api/education/assessment/history/route";

describe("education assessment history API route", () => {
  beforeEach(() => {
    cookieGet.mockReset();
    vi.unstubAllGlobals();
  });

  it("returns 401 locally when the session cookie is missing", async () => {
    cookieGet.mockReturnValue(undefined);
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await GET();

    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({ detail: "Not authenticated" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("forwards authenticated history requests with no-store", async () => {
    cookieGet.mockReturnValue({ value: "session-token" });
    const attempts = [{ id: 1, question_id: "q1", selected_option: 0, score: 0, passed: false }];
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(attempts), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await GET();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/education/assessment/history",
      {
        headers: { authorization: "Bearer session-token" },
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(attempts);
  });

  it("returns a stable 503 without leaking backend details", async () => {
    cookieGet.mockReturnValue({ value: "session-token" });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED secret-host")));

    const response = await GET();
    const payload = await response.json();

    expect(response.status).toBe(503);
    expect(payload).toEqual({ detail: "Education assessment history service is unavailable" });
    expect(JSON.stringify(payload)).not.toContain("secret-host");
  });
});
