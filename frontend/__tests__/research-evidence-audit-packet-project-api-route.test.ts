import { beforeEach, describe, expect, it, vi } from "vitest";

const cookiesMock = vi.fn();

vi.mock("next/headers", () => ({
  cookies: cookiesMock,
}));

process.env.BACKEND_URL = "http://backend:8000";

const { GET } = await import("../app/api/research-evidence-audit-packet/[projectId]/route");

function context(projectId: string) {
  return { params: Promise.resolve({ projectId }) };
}

describe("research evidence audit packet project API route", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    cookiesMock.mockReset();
  });

  it("returns 401 without a session and does not call the backend", async () => {
    cookiesMock.mockResolvedValue({ get: vi.fn().mockReturnValue(undefined) });
    const fetchMock = vi.spyOn(globalThis, "fetch");

    const response = await GET(new Request("http://localhost/api/research-evidence-audit-packet/12"), context("12"));

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ detail: "Not authenticated" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns 400 for a non-numeric project and does not call the backend", async () => {
    cookiesMock.mockResolvedValue({ get: vi.fn().mockReturnValue({ value: "session-token" }) });
    const fetchMock = vi.spyOn(globalThis, "fetch");

    const response = await GET(new Request("http://localhost/api/research-evidence-audit-packet/not-a-number"), context("not-a-number"));

    expect(response.status).toBe(400);
    await expect(response.json()).resolves.toEqual({ detail: "Invalid project" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("forwards authentication and preserves upstream status and body", async () => {
    cookiesMock.mockResolvedValue({ get: vi.fn().mockReturnValue({ value: "session-token" }) });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ packet: "ready" }), {
        status: 202,
        headers: { "content-type": "application/json" },
      }),
    );

    const response = await GET(new Request("http://localhost/api/research-evidence-audit-packet/42"), context("42"));

    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend:8000/api/v1/research-evidence-audit-packet/42",
      {
        headers: { authorization: "Bearer session-token" },
        cache: "no-store",
      },
    );
    expect(response.status).toBe(202);
    expect(response.headers.get("content-type")).toContain("application/json");
    await expect(response.json()).resolves.toEqual({ packet: "ready" });
  });

  it("returns a controlled 503 when the backend request fails", async () => {
    cookiesMock.mockResolvedValue({ get: vi.fn().mockReturnValue({ value: "session-token" }) });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("connection refused"));

    const response = await GET(new Request("http://localhost/api/research-evidence-audit-packet/42"), context("42"));

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Research evidence audit packet service unavailable",
    });
  });

  it("returns a controlled 503 when the upstream body cannot be read", async () => {
    cookiesMock.mockResolvedValue({ get: vi.fn().mockReturnValue({ value: "session-token" }) });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      text: vi.fn().mockRejectedValue(new Error("body read failed")),
    } as unknown as Response);

    const response = await GET(new Request("http://localhost/api/research-evidence-audit-packet/42"), context("42"));

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Research evidence audit packet response unavailable",
    });
  });
});
