import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { GET, POST } from "@/app/api/research-projects/route";

describe("research-projects API proxy", () => {
  beforeEach(() => {
    getCookie.mockReset();
    vi.restoreAllMocks();
  });

  it("returns 401 without calling the backend when no session exists", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchMock = vi.spyOn(globalThis, "fetch");

    const response = await GET(new Request("http://localhost/api/research-projects"));

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ detail: "Not authenticated" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("preserves GET response and authenticated no-store forwarding", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([{ id: 1, title: "Project" }]), { status: 200 }),
    );

    const response = await GET(new Request("http://localhost/api/research-projects"));

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/v1/research-projects", {
      method: "GET",
      headers: {
        authorization: "Bearer session-value",
        "content-type": "application/json",
      },
      body: undefined,
      cache: "no-store",
    });
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual([{ id: 1, title: "Project" }]);
  });

  it("forwards POST body and preserves upstream status", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: 2, title: "New project" }), { status: 201 }),
    );
    const body = JSON.stringify({ title: "New project" });

    const response = await POST(
      new Request("http://localhost/api/research-projects", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body,
      }),
    );

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/v1/research-projects", {
      method: "POST",
      headers: {
        authorization: "Bearer session-value",
        "content-type": "application/json",
      },
      body,
      cache: "no-store",
    });
    expect(response.status).toBe(201);
    await expect(response.json()).resolves.toEqual({ id: 2, title: "New project" });
  });

  it("preserves upstream error status and body", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Invalid project" }), { status: 422 }),
    );

    const response = await POST(
      new Request("http://localhost/api/research-projects", {
        method: "POST",
        body: JSON.stringify({ title: "" }),
      }),
    );

    expect(response.status).toBe(422);
    await expect(response.json()).resolves.toEqual({ detail: "Invalid project" });
  });

  it("returns a stable 503 without exposing backend failure details", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new Error("http://internal-backend:8000 failed with session-value"),
    );

    const response = await GET(new Request("http://localhost/api/research-projects"));
    const responseBody = await response.json();

    expect(response.status).toBe(503);
    expect(responseBody).toEqual({ detail: "Research projects service is unavailable" });
    expect(JSON.stringify(responseBody)).not.toContain("internal-backend");
    expect(JSON.stringify(responseBody)).not.toContain("session-value");
  });
});
