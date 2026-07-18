import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { PATCH } from "@/app/api/personal-memory/[memoryId]/route";

const context = (memoryId: string) => ({ params: Promise.resolve({ memoryId }) });

describe("personal memory revision proxy", () => {
  beforeEach(() => {
    getCookie.mockReset();
    vi.restoreAllMocks();
  });

  it("requires authentication without reading the request body or calling the backend", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const response = await PATCH(
      new Request("http://localhost/api/personal-memory/17", {
        method: "PATCH",
        body: JSON.stringify({ summary: "Updated" }),
      }),
      context("17"),
    );

    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("encodes identifiers and forwards the JSON revision payload with no-store", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: 17, revision_number: 2 }), { status: 200 }),
    );
    const payload = {
      statement: "Prefer primary evidence.",
      summary: "Primary evidence first",
      category: "learning_goal",
      confidence: 0.85,
      status: "validated",
    };

    const response = await PATCH(
      new Request("http://localhost/api/personal-memory/memory%20%2F%201", {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      }),
      context("memory / 1"),
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/knowledge-memory/memory%20%2F%201",
      {
        method: "PATCH",
        headers: {
          authorization: "Bearer session-value",
          "content-type": "application/json",
        },
        body: JSON.stringify(payload),
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ id: 17, revision_number: 2 });
  });

  it("preserves backend validation responses", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Validated memory requires confidence of at least 0.5" }), {
        status: 422,
      }),
    );

    const response = await PATCH(
      new Request("http://localhost/api/personal-memory/17", {
        method: "PATCH",
        body: JSON.stringify({ status: "validated", confidence: 0.2 }),
      }),
      context("17"),
    );

    expect(response.status).toBe(422);
    expect(await response.json()).toEqual({
      detail: "Validated memory requires confidence of at least 0.5",
    });
  });

  it("returns a stable secret-safe outage response", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new Error("http://internal-backend failed with session-value"),
    );

    const response = await PATCH(
      new Request("http://localhost/api/personal-memory/17", {
        method: "PATCH",
        body: JSON.stringify({ summary: "Updated" }),
      }),
      context("17"),
    );
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Personal memory service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("internal-backend");
    expect(JSON.stringify(body)).not.toContain("session-value");
  });
});
