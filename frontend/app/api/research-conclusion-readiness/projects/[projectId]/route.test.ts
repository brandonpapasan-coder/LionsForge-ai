import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { GET } from "@/app/api/research-conclusion-readiness/projects/[projectId]/route";

const context = (projectId: string) => ({ params: Promise.resolve({ projectId }) });

describe("conclusion-readiness API proxy", () => {
  beforeEach(() => {
    getCookie.mockReset();
    vi.restoreAllMocks();
  });

  it("returns 401 without calling the backend when no session exists", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchMock = vi.spyOn(globalThis, "fetch");

    const response = await GET(new Request("http://localhost"), context("project-1"));

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ detail: "Not authenticated" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("encodes the project identifier and preserves an upstream response", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ readiness_score: 0.9 }), { status: 200 }),
    );

    const response = await GET(new Request("http://localhost"), context("project / alpha"));

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/research-conclusion-readiness/projects/project%20%2F%20alpha",
      {
        headers: { authorization: "Bearer session-value" },
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ readiness_score: 0.9 });
  });

  it("preserves upstream error status and body", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Not found" }), { status: 404 }),
    );

    const response = await GET(new Request("http://localhost"), context("missing"));

    expect(response.status).toBe(404);
    await expect(response.json()).resolves.toEqual({ detail: "Not found" });
  });

  it("returns a stable 503 without exposing backend failure details", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("connection failed"));

    const response = await GET(new Request("http://localhost"), context("project-1"));
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Conclusion readiness service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("connection failed");
  });

  it("returns a stable 503 when the upstream response body cannot be read", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      text: vi.fn().mockRejectedValue(new Error("upstream body leaked")),
    } as unknown as Response);

    const response = await GET(new Request("http://localhost"), context("project-1"));
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Conclusion readiness service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("upstream body leaked");
  });
});