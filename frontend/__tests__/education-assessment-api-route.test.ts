import { beforeEach, describe, expect, it, vi } from "vitest";

const cookieGet = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: cookieGet })),
}));

import { GET, POST } from "@/app/api/education/assessment/route";

describe("education assessment API route", () => {
  beforeEach(() => {
    cookieGet.mockReset();
    vi.unstubAllGlobals();
  });

  it("returns 401 locally when the session cookie is missing", async () => {
    cookieGet.mockReturnValue(undefined);
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await GET();

    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({ detail: "Not authenticated" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("forwards authenticated GET requests with no-store", async () => {
    cookieGet.mockReturnValue({ value: "session-token" });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ assessment: "ready" }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await GET();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/education/assessment",
      expect.objectContaining({
        method: "GET",
        headers: { authorization: "Bearer session-token" },
        body: undefined,
        cache: "no-store",
      }),
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ assessment: "ready" });
  });

  it("forwards authenticated POST bodies and JSON headers with no-store", async () => {
    cookieGet.mockReturnValue({ value: "session-token" });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ score: 92 }), { status: 201 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const request = new Request("http://localhost/api/education/assessment", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ answers: ["a", "b"] }),
    });

    const response = await POST(request as never);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/education/assessment",
      expect.objectContaining({
        method: "POST",
        headers: {
          authorization: "Bearer session-token",
          "content-type": "application/json",
        },
        body: JSON.stringify({ answers: ["a", "b"] }),
        cache: "no-store",
      }),
    );
    expect(response.status).toBe(201);
    expect(await response.json()).toEqual({ score: 92 });
  });

  it("returns 400 when reading the POST body fails", async () => {
    cookieGet.mockReturnValue({ value: "session-token" });
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const request = {
      text: vi.fn().mockRejectedValue(new Error("request stream failed")),
    } as never;

    const response = await POST(request);

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ detail: "Invalid request body" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each([
    ["GET", async () => GET()],
    [
      "POST",
      async () =>
        POST(
          new Request("http://localhost/api/education/assessment", {
            method: "POST",
            body: "{}",
          }) as never,
        ),
    ],
  ])("returns a stable 503 when %s cannot reach the backend", async (_method, invoke) => {
    cookieGet.mockReturnValue({ value: "session-token" });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connect ECONNREFUSED secret-host")));

    const response = await invoke();
    const payload = await response.json();

    expect(response.status).toBe(503);
    expect(payload).toEqual({ detail: "Education assessment service is unavailable" });
    expect(JSON.stringify(payload)).not.toContain("secret-host");
  });

  it("returns a stable 503 when the upstream body cannot be read", async () => {
    cookieGet.mockReturnValue({ value: "session-token" });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 200,
        text: vi.fn().mockRejectedValue(new Error("upstream stream leaked-path")),
      }),
    );

    const response = await GET();
    const payload = await response.json();

    expect(response.status).toBe(503);
    expect(payload).toEqual({ detail: "Education assessment service is unavailable" });
    expect(JSON.stringify(payload)).not.toContain("leaked-path");
  });
});
