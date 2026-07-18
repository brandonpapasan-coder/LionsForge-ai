import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { GET, POST } from "@/app/api/research-projects/[projectId]/sessions/route";

const context = (projectId: string) => ({ params: Promise.resolve({ projectId }) });

describe("research project sessions API proxy", () => {
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

  it("encodes the project identifier for GET and preserves the upstream response", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([{ id: "session-1" }]), { status: 200 }),
    );

    const response = await GET(
      new Request("http://localhost"),
      context("project / alpha"),
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/research-projects/project%20%2F%20alpha/sessions",
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
    await expect(response.json()).resolves.toEqual([{ id: "session-1" }]);
  });

  it("forwards the POST body and preserves the upstream response", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "session-2" }), { status: 201 }),
    );
    const requestBody = JSON.stringify({ objective: "Review evidence" });

    const response = await POST(
      new Request("http://localhost", { method: "POST", body: requestBody }),
      context("project-1"),
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/research-projects/project-1/sessions",
      {
        method: "POST",
        headers: {
          authorization: "Bearer session-value",
          "content-type": "application/json",
        },
        body: requestBody,
        cache: "no-store",
      },
    );
    expect(response.status).toBe(201);
    await expect(response.json()).resolves.toEqual({ id: "session-2" });
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

  it("returns a controlled 400 when the POST body cannot be read", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const request = {
      method: "POST",
      text: vi.fn().mockRejectedValue(new Error("secret client stream")),
    } as unknown as Request;

    const response = await POST(request, context("project-1"));
    const body = await response.json();

    expect(response.status).toBe(400);
    expect(body).toEqual({ detail: "Invalid request body" });
    expect(JSON.stringify(body)).not.toContain("secret client stream");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns a stable 503 without exposing backend failure details", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new Error("http://internal-backend:8000 failed with session-value"),
    );

    const response = await POST(
      new Request("http://localhost", { method: "POST", body: "{}" }),
      context("project-1"),
    );
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Research sessions service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("internal-backend");
    expect(JSON.stringify(body)).not.toContain("session-value");
  });

  it("returns a stable 503 when the upstream response body cannot be read", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      text: vi.fn().mockRejectedValue(new Error("upstream stream leaked-path")),
    } as unknown as Response);

    const response = await GET(new Request("http://localhost"), context("project-1"));
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Research sessions service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("leaked-path");
  });
});
