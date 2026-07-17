import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();
vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

const { GET } = await import(
  "../app/api/research-evidence-review-actions/projects/[projectId]/route"
);

const context = (projectId: string) => ({ params: Promise.resolve({ projectId }) });

describe("project review actions proxy", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    getCookie.mockReset();
  });

  it("returns 401 without a session", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const response = await GET(new Request("http://localhost"), context("project-1"));

    expect(response.status).toBe(401);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("encodes projectId and forwards authentication with no-store", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"actions":[]}', { status: 200 }),
    );

    const response = await GET(
      new Request("http://localhost"),
      context("project/alpha beta"),
    );

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/v1/research-evidence-audit/projects/project%2Falpha%20beta/review-actions",
      {
        headers: { authorization: "Bearer session-token" },
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("application/json");
    expect(await response.text()).toBe('{"actions":[]}');
  });

  it("preserves upstream status and body", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"detail":"missing"}', { status: 404 }),
    );

    const response = await GET(new Request("http://localhost"), context("missing"));

    expect(response.status).toBe(404);
    expect(await response.text()).toBe('{"detail":"missing"}');
  });

  it("returns a controlled 503 when the backend request fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("backend failure"));

    const response = await GET(new Request("http://localhost"), context("project-1"));

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      detail: "Project review actions service is temporarily unavailable",
    });
  });

  it("returns a controlled 503 when the upstream body cannot be read", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      text: vi.fn().mockRejectedValue(new Error("stream failure")),
    } as unknown as Response);

    const response = await GET(new Request("http://localhost"), context("project-1"));

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      detail: "Project review actions service is temporarily unavailable",
    });
  });
});
