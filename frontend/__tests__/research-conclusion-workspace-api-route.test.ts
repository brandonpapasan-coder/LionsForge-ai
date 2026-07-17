import { beforeEach, describe, expect, it, vi } from "vitest";

const cookieGet = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: cookieGet })),
}));

import { GET, PUT } from "@/app/api/research-conclusion-workspace/[projectId]/route";

const context = { params: Promise.resolve({ projectId: "project/alpha" }) };

beforeEach(() => {
  vi.restoreAllMocks();
  cookieGet.mockReset();
  cookieGet.mockReturnValue({ value: "session-token" });
});

describe("research conclusion workspace API route", () => {
  it("requires authentication", async () => {
    cookieGet.mockReturnValue(undefined);
    const response = await GET(new Request("http://localhost/api"), context);
    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ detail: "Not authenticated" });
  });

  it("forwards GET requests with encoded project IDs", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ status: "ready" }), { status: 200 }),
    );
    const response = await GET(new Request("http://localhost/api"), context);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/research-conclusions/projects/project%2Falpha",
      expect.objectContaining({ method: "GET", body: undefined, cache: "no-store" }),
    );
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ status: "ready" });
  });

  it("forwards PUT request bodies", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ updated: true }), { status: 202 }),
    );
    const request = new Request("http://localhost/api", {
      method: "PUT",
      body: JSON.stringify({ conclusion: "supported" }),
    });
    const response = await PUT(request, context);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/research-conclusions/projects/project%2Falpha",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ conclusion: "supported" }),
        headers: {
          authorization: "Bearer session-token",
          "content-type": "application/json",
        },
        cache: "no-store",
      }),
    );
    expect(response.status).toBe(202);
  });

  it("returns 400 when the PUT body cannot be read", async () => {
    const request = {
      method: "PUT",
      text: vi.fn().mockRejectedValue(new Error("unreadable")),
    } as unknown as Request;
    const response = await PUT(request, context);
    expect(response.status).toBe(400);
    await expect(response.json()).resolves.toEqual({ detail: "Invalid request body" });
  });

  it("returns 503 when the backend request fails", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("offline"));
    const response = await GET(new Request("http://localhost/api"), context);
    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Research conclusion workspace service unavailable",
    });
  });

  it("returns 503 when the upstream body cannot be read", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      text: vi.fn().mockRejectedValue(new Error("stream failed")),
    } as unknown as Response);
    const response = await GET(new Request("http://localhost/api"), context);
    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Research conclusion workspace service unavailable",
    });
  });
});
