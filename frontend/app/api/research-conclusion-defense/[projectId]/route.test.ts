import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { GET, PUT } from "@/app/api/research-conclusion-defense/[projectId]/route";

const context = (projectId: string) => ({ params: Promise.resolve({ projectId }) });

describe("conclusion-defense API proxy", () => {
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

  it("encodes the project identifier and preserves a GET response", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ score: 0.8 }), { status: 200 }),
    );

    const response = await GET(new Request("http://localhost"), context("project / alpha"));

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/research-conclusion-defense/projects/project%20%2F%20alpha",
      {
        method: "GET",
        headers: {
          authorization: "Bearer session-value",
          "content-type": "application/json",
        },
        body: undefined,
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ score: 0.8 });
  });

  it("forwards the PUT body and preserves an upstream error", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Conflict" }), { status: 409 }),
    );
    const body = JSON.stringify({ conclusion: "revised" });

    const response = await PUT(
      new Request("http://localhost", { method: "PUT", body }),
      context("project-1"),
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/research-conclusion-defense/projects/project-1",
      {
        method: "PUT",
        headers: {
          authorization: "Bearer session-value",
          "content-type": "application/json",
        },
        body,
        cache: "no-store",
      },
    );
    expect(response.status).toBe(409);
    await expect(response.json()).resolves.toEqual({ detail: "Conflict" });
  });

  it("returns 400 when a PUT request body cannot be read", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const request = new Request("http://localhost", { method: "PUT", body: "{}" });
    vi.spyOn(request, "text").mockRejectedValue(new Error("body read failed"));

    const response = await PUT(request, context("project-1"));

    expect(response.status).toBe(400);
    await expect(response.json()).resolves.toEqual({
      detail: "Unable to read conclusion defense request body",
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each([
    ["GET", (request: Request) => GET(request, context("project-1"))],
    ["PUT", (request: Request) => PUT(request, context("project-1"))],
  ])("returns a stable 503 for %s backend failures", async (method, callRoute) => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new Error("http://internal-backend:8000 secret-session-value"),
    );
    const request = new Request("http://localhost", {
      method,
      body: method === "PUT" ? JSON.stringify({ conclusion: "draft" }) : undefined,
    });

    const response = await callRoute(request);
    const responseBody = await response.json();

    expect(response.status).toBe(503);
    expect(responseBody).toEqual({ detail: "Conclusion defense service is unavailable" });
    expect(JSON.stringify(responseBody)).not.toContain("internal-backend");
    expect(JSON.stringify(responseBody)).not.toContain("secret-session-value");
  });

  it("returns a stable 503 when the upstream body cannot be read", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const upstream = new Response(JSON.stringify({ score: 0.8 }), { status: 200 });
    vi.spyOn(upstream, "text").mockRejectedValue(new Error("response read failed"));
    vi.spyOn(globalThis, "fetch").mockResolvedValue(upstream);

    const response = await GET(new Request("http://localhost"), context("project-1"));

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Conclusion defense service is unavailable",
    });
  });
});
