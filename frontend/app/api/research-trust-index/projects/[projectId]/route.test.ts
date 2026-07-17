import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { GET } from "@/app/api/research-trust-index/projects/[projectId]/route";

const context = (projectId: string) => ({ params: Promise.resolve({ projectId }) });

describe("project research-trust API proxy", () => {
  beforeEach(() => {
    getCookie.mockReset();
    vi.restoreAllMocks();
  });

  it("returns 401 without calling the backend when no session exists", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchMock = vi.spyOn(globalThis, "fetch");

    const response = await GET(new Request("http://localhost"), context("7"));

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ detail: "Not authenticated" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns 404 without calling the backend for an invalid project ID", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch");

    const response = await GET(new Request("http://localhost"), context("bad-id"));

    expect(response.status).toBe(404);
    await expect(response.json()).resolves.toEqual({ detail: "Research project not found" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("forwards authentication and preserves an upstream success response", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ trust_score: 0.88 }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const response = await GET(new Request("http://localhost"), context("7"));

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/research-trust-index/projects/7",
      {
        headers: { authorization: "Bearer session-value" },
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ trust_score: 0.88 });
  });

  it("preserves an upstream error status and body", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Research project not found" }), {
        status: 404,
        headers: { "content-type": "application/json" },
      }),
    );

    const response = await GET(new Request("http://localhost"), context("7"));

    expect(response.status).toBe(404);
    await expect(response.json()).resolves.toEqual({ detail: "Research project not found" });
  });

  it("returns a stable 503 without exposing backend failure details", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("backend connection failed"));

    const response = await GET(new Request("http://localhost"), context("7"));
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Research trust service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("connection failed");
  });

  it("returns the same stable 503 when the upstream body cannot be read", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      text: vi.fn().mockRejectedValue(new Error("upstream body exposed secret-value")),
    } as unknown as Response);

    const response = await GET(new Request("http://localhost"), context("7"));
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Research trust service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("secret-value");
  });
});
