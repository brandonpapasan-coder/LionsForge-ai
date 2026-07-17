import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();
vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

const { POST } = await import(
  "../app/api/research-evidence-review-actions/generate/route"
);

const request = (body = '{"project_id":"project-1"}') =>
  new Request("http://localhost/api/research-evidence-review-actions/generate", {
    method: "POST",
    body,
    headers: { "content-type": "application/json" },
  });

describe("research evidence review action generation proxy", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    getCookie.mockReset();
  });

  it("returns 401 without a session", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const response = await POST(request());

    expect(response.status).toBe(401);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("returns 400 for invalid JSON without calling the backend", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const response = await POST(request("{"));

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ detail: "Invalid JSON payload" });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("forwards the parsed payload and preserves upstream status and body", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"generated":true}', { status: 201 }),
    );

    const response = await POST(request('{"project_id":"project-2"}'));

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/research-evidence-audit/review-actions/generate",
      {
        method: "POST",
        headers: {
          authorization: "Bearer session-token",
          "content-type": "application/json",
        },
        body: '{"project_id":"project-2"}',
        cache: "no-store",
      },
    );
    expect(response.status).toBe(201);
    expect(response.headers.get("content-type")).toContain("application/json");
    expect(await response.text()).toBe('{"generated":true}');
  });

  it("preserves non-success upstream responses", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"detail":"conflict"}', { status: 409 }),
    );

    const response = await POST(request());

    expect(response.status).toBe(409);
    expect(await response.text()).toBe('{"detail":"conflict"}');
  });

  it("returns a controlled 503 when the backend request fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("backend failure"));

    const response = await POST(request());

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      detail: "Review action generation service is temporarily unavailable",
    });
  });

  it("returns a controlled 503 when the upstream body cannot be read", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      text: vi.fn().mockRejectedValue(new Error("stream failure")),
    } as unknown as Response);

    const response = await POST(request());

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      detail: "Review action generation service is temporarily unavailable",
    });
  });
});
