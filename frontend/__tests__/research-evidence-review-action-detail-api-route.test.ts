import { beforeEach, describe, expect, it, vi } from "vitest";

process.env.BACKEND_URL = "http://backend:8000";

const getCookie = vi.fn();
vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

const { PATCH } = await import(
  "../app/api/research-evidence-review-actions/[actionId]/route"
);

const context = (actionId: string) => ({ params: Promise.resolve({ actionId }) });
const request = (body = '{"status":"resolved"}') =>
  new Request("http://localhost", {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body,
  });

describe("review action detail proxy", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    getCookie.mockReset();
  });

  it("returns 401 without a session", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const response = await PATCH(request(), context("action-1"));

    expect(response.status).toBe(401);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("returns 400 for invalid JSON without contacting the backend", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const response = await PATCH(request("{"), context("action-1"));

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ detail: "Invalid JSON payload" });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("encodes actionId and forwards the PATCH payload with authentication and no-store", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"status":"resolved"}', { status: 200 }),
    );

    const response = await PATCH(request(), context("action/alpha beta"));

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/v1/research-evidence-audit/review-actions/action%2Falpha%20beta",
      {
        method: "PATCH",
        headers: {
          authorization: "Bearer session-token",
          "content-type": "application/json",
        },
        body: '{"status":"resolved"}',
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("application/json");
    expect(await response.text()).toBe('{"status":"resolved"}');
  });

  it("preserves upstream status and body", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"detail":"missing"}', { status: 404 }),
    );

    const response = await PATCH(request(), context("missing"));

    expect(response.status).toBe(404);
    expect(await response.text()).toBe('{"detail":"missing"}');
  });

  it("returns a controlled 503 when the backend request fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("backend failure"));

    const response = await PATCH(request(), context("action-1"));

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      detail: "Review action service is temporarily unavailable",
    });
  });

  it("returns a controlled 503 when the upstream body cannot be read", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      text: vi.fn().mockRejectedValue(new Error("stream failure")),
    } as unknown as Response);

    const response = await PATCH(request(), context("action-1"));

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      detail: "Review action service is temporarily unavailable",
    });
  });
});
