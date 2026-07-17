import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { GET } from "@/app/api/research-governance-dashboard/[projectId]/route";

const context = (projectId: string) => ({ params: Promise.resolve({ projectId }) });

describe("research governance dashboard API proxy", () => {
  beforeEach(() => {
    getCookie.mockReset();
    vi.restoreAllMocks();
  });

  it("returns 401 without calling the backend when no session exists", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchMock = vi.spyOn(globalThis, "fetch");

    const response = await GET(new Request("http://localhost/api?days=30"), context("project-1"));

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ detail: "Not authenticated" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each(["0", "366", "abc", "1.5", "-1"])(
    "rejects invalid days value %s without calling the backend",
    async (days) => {
      getCookie.mockReturnValue({ value: "session-token" });
      const fetchMock = vi.spyOn(globalThis, "fetch");

      const response = await GET(
        new Request(`http://localhost/api?days=${encodeURIComponent(days)}`),
        context("project-1"),
      );

      expect(response.status).toBe(400);
      await expect(response.json()).resolves.toEqual({ detail: "Invalid days value" });
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );

  it("encodes the project identifier and forwards a validated days value", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ status: "ready" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const response = await GET(
      new Request("http://localhost/api?days=45"),
      context("project/alpha beta"),
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/research-governance-dashboard/projects/project%2Falpha%20beta?days=45",
      {
        headers: { authorization: "Bearer session-token" },
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ status: "ready" });
  });

  it("defaults days to 30 and preserves upstream errors", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Project not found" }), {
        status: 404,
        headers: { "content-type": "application/json" },
      }),
    );

    const response = await GET(new Request("http://localhost/api"), context("42"));

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/research-governance-dashboard/projects/42?days=30",
      {
        headers: { authorization: "Bearer session-token" },
        cache: "no-store",
      },
    );
    expect(response.status).toBe(404);
    await expect(response.json()).resolves.toEqual({ detail: "Project not found" });
  });

  it("returns a stable 503 without exposing backend failure details", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new Error("connect ECONNREFUSED http://private-backend:8000 session-token"),
    );

    const response = await GET(new Request("http://localhost/api?days=30"), context("42"));
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Research governance service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("private-backend");
    expect(JSON.stringify(body)).not.toContain("session-token");
    expect(JSON.stringify(body)).not.toContain("ECONNREFUSED");
  });
});
