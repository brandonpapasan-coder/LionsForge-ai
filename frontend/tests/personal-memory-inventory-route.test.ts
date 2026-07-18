import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { GET } from "@/app/api/personal-memory/route";

describe("personal memory inventory API proxy", () => {
  beforeEach(() => {
    getCookie.mockReset();
    vi.restoreAllMocks();
  });

  it("requires authentication without calling the backend", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchMock = vi.spyOn(globalThis, "fetch");

    const response = await GET(new Request("http://localhost/api/personal-memory"));

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ detail: "Not authenticated" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("forwards supported filters with safe encoding and no-store", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([{ id: 17, summary: "Source evaluation" }]), { status: 200 }),
    );

    const response = await GET(
      new Request(
        "http://localhost/api/personal-memory?project_id=7&status=provisional&category=learning%20goal&query=primary%20sources&ignored=secret",
      ),
    );

    const [target, init] = fetchMock.mock.calls[0];
    expect(String(target)).toBe(
      "http://localhost:8000/api/v1/knowledge-memory?project_id=7&status=provisional&category=learning+goal&query=primary+sources",
    );
    expect(init).toEqual({
      method: "GET",
      headers: { authorization: "Bearer session-value" },
      cache: "no-store",
    });
    expect(String(target)).not.toContain("ignored");
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual([{ id: 17, summary: "Source evaluation" }]);
  });

  it("preserves upstream error status and body", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Research project not found" }), { status: 404 }),
    );

    const response = await GET(
      new Request("http://localhost/api/personal-memory?project_id=999"),
    );

    expect(response.status).toBe(404);
    await expect(response.json()).resolves.toEqual({ detail: "Research project not found" });
  });

  it("returns a stable 503 without exposing backend failure details", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new Error("http://internal-backend:8000 failed with session-value"),
    );

    const response = await GET(new Request("http://localhost/api/personal-memory"));
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Personal memory service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("internal-backend");
    expect(JSON.stringify(body)).not.toContain("session-value");
  });
});
