import { beforeEach, describe, expect, it, vi } from "vitest";

const cookieGet = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: cookieGet })),
}));

async function loadRoute() {
  vi.resetModules();
  return import("../app/api/mentor/chat/route");
}

describe("mentor chat API route", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    cookieGet.mockReset();
  });

  it("returns 401 without calling the backend when unauthenticated", async () => {
    cookieGet.mockReturnValue(undefined);
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const { POST } = await loadRoute();

    const response = await POST(new Request("http://localhost/api/mentor/chat", { method: "POST", body: "{}" }));

    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({ detail: "Not authenticated" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("forwards auth, JSON body, and no-store to the backend", async () => {
    cookieGet.mockReturnValue({ value: "session-token" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"reply":"ok"}', { status: 201, headers: { "content-type": "application/json" } }),
    );
    const { POST } = await loadRoute();
    const body = '{"message":"hello"}';

    const response = await POST(new Request("http://localhost/api/mentor/chat", { method: "POST", body }));

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/v1/mentor/chat", {
      method: "POST",
      headers: {
        authorization: "Bearer session-token",
        "content-type": "application/json",
      },
      body,
      cache: "no-store",
    });
    expect(response.status).toBe(201);
    expect(await response.text()).toBe('{"reply":"ok"}');
  });

  it("preserves upstream error status and body", async () => {
    cookieGet.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response('{"detail":"invalid"}', { status: 422 }));
    const { POST } = await loadRoute();

    const response = await POST(new Request("http://localhost/api/mentor/chat", { method: "POST", body: "{}" }));

    expect(response.status).toBe(422);
    expect(await response.text()).toBe('{"detail":"invalid"}');
  });

  it("returns a stable 503 when reading the request body fails", async () => {
    cookieGet.mockReturnValue({ value: "session-token" });
    const request = { text: vi.fn().mockRejectedValue(new Error("request stream failed")) } as unknown as Request;
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const { POST } = await loadRoute();

    const response = await POST(request);
    const text = await response.text();

    expect(response.status).toBe(503);
    expect(text).toContain("Mentor service is unavailable");
    expect(text).not.toContain("request stream failed");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns a stable 503 when the backend connection fails", async () => {
    cookieGet.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("connect ECONNREFUSED http://backend:8000"));
    const { POST } = await loadRoute();

    const response = await POST(new Request("http://localhost/api/mentor/chat", { method: "POST", body: "{}" }));
    const text = await response.text();

    expect(response.status).toBe(503);
    expect(text).toContain("Mentor service is unavailable");
    expect(text).not.toContain("ECONNREFUSED");
    expect(text).not.toContain("backend:8000");
  });

  it("returns a stable 503 when reading the upstream response fails", async () => {
    cookieGet.mockReturnValue({ value: "session-token" });
    const upstream = { status: 200, text: vi.fn().mockRejectedValue(new Error("upstream stream failed")) } as unknown as Response;
    vi.spyOn(globalThis, "fetch").mockResolvedValue(upstream);
    const { POST } = await loadRoute();

    const response = await POST(new Request("http://localhost/api/mentor/chat", { method: "POST", body: "{}" }));
    const text = await response.text();

    expect(response.status).toBe(503);
    expect(text).toContain("Mentor service is unavailable");
    expect(text).not.toContain("upstream stream failed");
  });
});
