import { beforeEach, describe, expect, it, vi } from "vitest";

const cookieGet = vi.fn();
vi.mock("next/headers", () => ({ cookies: vi.fn(async () => ({ get: cookieGet })) }));

import { GET } from "@/app/api/investigations/[investigationId]/validation-map/route";

const context = { params: Promise.resolve({ investigationId: "7" }) };

describe("claim evidence validation map API route", () => {
  beforeEach(() => {
    cookieGet.mockReset();
    vi.unstubAllGlobals();
  });

  it("returns 401 without a session", async () => {
    cookieGet.mockReturnValue(undefined);
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const response = await GET(new Request("http://localhost/api") as never, context);
    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({ detail: "Not authenticated" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("forwards authenticated requests with no-store", async () => {
    cookieGet.mockReturnValue({ value: "session-token" });
    const payload = { status: "empty", claims: [] };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const response = await GET(new Request("http://localhost/api") as never, context);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/investigations/7/validation-map",
      { headers: { authorization: "Bearer session-token" }, cache: "no-store" },
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(payload);
  });

  it("returns a stable 503 without leaking backend details", async () => {
    cookieGet.mockReturnValue({ value: "session-token" });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("secret-host")));
    const response = await GET(new Request("http://localhost/api") as never, context);
    const payload = await response.json();
    expect(response.status).toBe(503);
    expect(payload).toEqual({ detail: "Claim evidence validation service is unavailable" });
    expect(JSON.stringify(payload)).not.toContain("secret-host");
  });
});
