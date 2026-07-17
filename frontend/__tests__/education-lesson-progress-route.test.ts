import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { PUT } from "@/app/api/education/lessons/[lessonSlug]/progress/route";

describe("education lesson progress route", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    getCookie.mockReset();
  });

  it("returns 401 without a session and does not call the backend", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const response = await PUT(
      new Request("http://localhost/api/education/lessons/test/progress", {
        method: "PUT",
        body: JSON.stringify({ completed: true }),
      }),
      { params: Promise.resolve({ lessonSlug: "test" }) },
    );

    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({ detail: "Not authenticated" });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("forwards the encoded lesson slug, bearer token, JSON body, and no-store", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ completed: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    const body = JSON.stringify({ completed: true, score: 95 });

    const response = await PUT(
      new Request("http://localhost/api/education/lessons/lesson/progress", {
        method: "PUT",
        body,
      }),
      { params: Promise.resolve({ lessonSlug: "lesson one/advanced" }) },
    );

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/education/lessons/lesson%20one%2Fadvanced/progress",
      {
        method: "PUT",
        headers: {
          authorization: "Bearer session-token",
          "content-type": "application/json",
        },
        body,
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ completed: true });
  });

  it("preserves upstream status and response body", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Invalid progress state" }), {
        status: 422,
      }),
    );

    const response = await PUT(
      new Request("http://localhost/api/education/lessons/test/progress", {
        method: "PUT",
        body: JSON.stringify({ completed: true }),
      }),
      { params: Promise.resolve({ lessonSlug: "test" }) },
    );

    expect(response.status).toBe(422);
    expect(await response.json()).toEqual({ detail: "Invalid progress state" });
  });

  it("returns a stable non-sensitive 503 when the service is unavailable", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new Error("connect ECONNREFUSED 10.0.0.7:8000 secret-internal-host"),
    );

    const response = await PUT(
      new Request("http://localhost/api/education/lessons/test/progress", {
        method: "PUT",
        body: JSON.stringify({ completed: true }),
      }),
      { params: Promise.resolve({ lessonSlug: "test" }) },
    );
    const payload = await response.json();

    expect(response.status).toBe(503);
    expect(payload).toEqual({ detail: "Lesson progress service is unavailable" });
    expect(JSON.stringify(payload)).not.toContain("10.0.0.7");
    expect(JSON.stringify(payload)).not.toContain("secret-internal-host");
  });

  it("returns the same stable 503 when reading the upstream body fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      text: vi.fn().mockRejectedValue(new Error("stream reset internal detail")),
    } as unknown as Response);

    const response = await PUT(
      new Request("http://localhost/api/education/lessons/test/progress", {
        method: "PUT",
        body: JSON.stringify({ completed: true }),
      }),
      { params: Promise.resolve({ lessonSlug: "test" }) },
    );

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      detail: "Lesson progress service is unavailable",
    });
  });
});
