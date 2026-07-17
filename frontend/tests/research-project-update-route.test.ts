import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { PATCH } from "@/app/api/research-projects/[projectId]/route";

const context = (projectId: string) => ({ params: Promise.resolve({ projectId }) });

describe("research project update API proxy", () => {
  beforeEach(() => {
    getCookie.mockReset();
    vi.restoreAllMocks();
  });

  it("returns 401 without calling the backend when no session exists", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchMock = vi.spyOn(globalThis, "fetch");

    const response = await PATCH(
      new Request("http://localhost", { method: "PATCH", body: "{}" }),
      context("project-1"),
    );

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ detail: "Not authenticated" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("encodes the project identifier and forwards the PATCH body", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "project / alpha", title: "Updated" }), {
        status: 200,
      }),
    );

    const response = await PATCH(
      new Request("http://localhost", {
        method: "PATCH",
        body: JSON.stringify({ title: "Updated" }),
      }),
      context("project / alpha"),
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/research-projects/project%20%2F%20alpha",
      {
        method: "PATCH",
        headers: {
          authorization: "Bearer session-value",
          "content-type": "application/json",
        },
        body: JSON.stringify({ title: "Updated" }),
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({
      id: "project / alpha",
      title: "Updated",
    });
  });

  it("preserves upstream error status and body", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Not found" }), { status: 404 }),
    );

    const response = await PATCH(
      new Request("http://localhost", { method: "PATCH", body: "{}" }),
      context("missing"),
    );

    expect(response.status).toBe(404);
    await expect(response.json()).resolves.toEqual({ detail: "Not found" });
  });

  it("returns a stable 503 without exposing backend failure details", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new Error("http://internal-backend:8000 failed with session-value"),
    );

    const response = await PATCH(
      new Request("http://localhost", { method: "PATCH", body: "{}" }),
      context("project-1"),
    );
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Research project service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("internal-backend");
    expect(JSON.stringify(body)).not.toContain("session-value");
  });
});
