import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { GET } from "@/app/api/personal-memory/evidence-health/route";

describe("personal memory evidence health inventory proxy", () => {
  beforeEach(() => {
    getCookie.mockReset();
    vi.restoreAllMocks();
  });

  it("requires authentication without calling the backend", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchMock = vi.spyOn(globalThis, "fetch");

    const response = await GET(new Request("http://localhost/api/personal-memory/evidence-health"));

    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("forwards supported filters and preserves the backend response", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const payload = { total_count: 1, by_classification: { weak: 1 }, items: [{ memory_id: 7 }] };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200 }),
    );

    const response = await GET(new Request(
      "http://localhost/api/personal-memory/evidence-health?project_id=4&classification=weak&ignored=value",
    ));

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/knowledge-memory/evidence-health/inventory?project_id=4&classification=weak",
      {
        method: "GET",
        headers: { authorization: "Bearer session-value" },
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(payload);
  });

  it("returns a stable secret-safe unavailable response", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new Error("http://internal-backend failed with session-value"),
    );

    const response = await GET(new Request("http://localhost/api/personal-memory/evidence-health"));
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Personal memory evidence health service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("internal-backend");
    expect(JSON.stringify(body)).not.toContain("session-value");
  });
});
