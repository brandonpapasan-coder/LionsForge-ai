import { beforeEach, describe, expect, it, vi } from "vitest";

process.env.BACKEND_URL = "http://backend:8000";

const getCookie = vi.fn();
vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

const { GET, POST, PUT } = await import(
  "../app/api/research-governance-digest/[...path]/route"
);

const context = (path: string[]) => ({ params: Promise.resolve({ path }) });

beforeEach(() => {
  vi.restoreAllMocks();
  getCookie.mockReset();
});

describe("research governance digest proxy", () => {
  it("returns 401 without a session", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const response = await GET(
      new Request("http://localhost/api/research-governance-digest/projects"),
      context(["projects"]),
    );

    expect(response.status).toBe(401);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("encodes each path segment, preserves query parameters, and forwards GET", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"items":[]}', { status: 200 }),
    );

    const response = await GET(
      new Request("http://localhost/api/research-governance-digest/projects/a?limit=10&mode=full"),
      context(["projects", "alpha/beta", "review notes"]),
    );

    expect(fetchSpy).toHaveBeenCalledWith(
      new URL(
        "http://backend:8000/api/v1/research-governance-digest/projects/alpha%2Fbeta/review%20notes?limit=10&mode=full",
      ),
      {
        method: "GET",
        headers: { authorization: "Bearer session-token" },
        body: undefined,
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
    expect(await response.text()).toBe('{"items":[]}');
  });

  it("forwards POST payload and content type", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"created":true}', { status: 201 }),
    );

    const response = await POST(
      new Request("http://localhost/api/research-governance-digest/generate", {
        method: "POST",
        body: '{"scope":"project"}',
      }),
      context(["generate"]),
    );

    expect(fetchSpy).toHaveBeenCalledWith(
      new URL("http://backend:8000/api/v1/research-governance-digest/generate"),
      {
        method: "POST",
        headers: {
          authorization: "Bearer session-token",
          "content-type": "application/json",
        },
        body: '{"scope":"project"}',
        cache: "no-store",
      },
    );
    expect(response.status).toBe(201);
  });

  it("preserves upstream status and body for PUT", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"detail":"conflict"}', { status: 409 }),
    );

    const response = await PUT(
      new Request("http://localhost/api/research-governance-digest/settings", {
        method: "PUT",
        body: '{"enabled":true}',
      }),
      context(["settings"]),
    );

    expect(response.status).toBe(409);
    expect(response.headers.get("content-type")).toContain("application/json");
    expect(await response.text()).toBe('{"detail":"conflict"}');
  });

  it("returns controlled 503 when the backend request fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("backend failure"));

    const response = await GET(
      new Request("http://localhost/api/research-governance-digest/projects"),
      context(["projects"]),
    );

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      detail: "Research governance digest service is temporarily unavailable",
    });
  });

  it("returns controlled 503 when the upstream body cannot be read", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      text: vi.fn().mockRejectedValue(new Error("stream failure")),
    } as unknown as Response);

    const response = await GET(
      new Request("http://localhost/api/research-governance-digest/projects"),
      context(["projects"]),
    );

    expect(response.status).toBe(503);
  });
});
