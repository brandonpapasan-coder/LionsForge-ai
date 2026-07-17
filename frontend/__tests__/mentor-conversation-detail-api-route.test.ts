import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { GET } from "@/app/api/mentor/conversations/[conversationId]/route";

const request = new Request("http://localhost/api/mentor/conversations/conversation-1");
const context = (conversationId = "conversation-1") => ({
  params: Promise.resolve({ conversationId }),
});

describe("mentor conversation detail API route", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    getCookie.mockReset();
  });

  it("returns 401 without a session and does not call the backend", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const response = await GET(request, context());

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ detail: "Not authenticated" });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("encodes the conversation ID, forwards authentication, disables caching, and preserves the upstream response", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "conversation/with spaces" }), {
        status: 206,
        headers: { "content-type": "application/json" },
      }),
    );

    const response = await GET(request, context("conversation/with spaces"));

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/mentor/conversations/conversation%2Fwith%20spaces",
      {
        headers: { authorization: "Bearer session-token" },
        cache: "no-store",
      },
    );
    expect(response.status).toBe(206);
    await expect(response.json()).resolves.toEqual({ id: "conversation/with spaces" });
  });

  it("returns a stable non-sensitive 503 when route parameters cannot be resolved", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const response = await GET(request, {
      params: Promise.reject(new Error("route internals exposed")),
    });
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Mentor service is unavailable" });
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(JSON.stringify(body)).not.toContain("route internals");
  });

  it("returns a stable non-sensitive 503 when the backend connection fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new Error("connect ECONNREFUSED http://internal-backend:8000"),
    );

    const response = await GET(request, context());
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Mentor service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("internal-backend");
    expect(JSON.stringify(body)).not.toContain("ECONNREFUSED");
  });

  it("returns the same stable 503 when reading the upstream body fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      text: vi.fn().mockRejectedValue(new Error("upstream stream failed")),
    } as unknown as Response);

    const response = await GET(request, context());

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Mentor service is unavailable",
    });
  });
});
