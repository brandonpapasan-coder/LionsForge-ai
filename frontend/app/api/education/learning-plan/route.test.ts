import { beforeEach, describe, expect, it, vi } from "vitest";

const cookieGet = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: cookieGet })),
}));

import { GET } from "@/app/api/education/learning-plan/route";

describe("education learning plan API route", () => {
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

  it("forwards authenticated learning-plan requests with no-store", async () => {
    cookieGet.mockReturnValue({ value: "session-token" });
    const plan = { status: "completed", generated_from: "measured_rules", advisory_notice: "Advisory only.", items: [] };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(plan), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await GET();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/education/learning-plan",
      {
        headers: { authorization: "Bearer session-token" },
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(plan);
  });

  it("returns a stable 503 without leaking backend details", async () => {
    cookieGet.mockReturnValue({ value: "session-token" });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED secret-host")));

    const response = await GET();
    const payload = await response.json();

    expect(response.status).toBe(503);
    expect(payload).toEqual({ detail: "Education learning plan service is unavailable" });
    expect(JSON.stringify(payload)).not.toContain("secret-host");
  });
});
