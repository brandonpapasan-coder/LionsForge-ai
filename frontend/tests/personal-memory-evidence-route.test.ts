import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { GET } from "@/app/api/personal-memory/[memoryId]/evidence/route";

const context = (memoryId: string) => ({ params: Promise.resolve({ memoryId }) });

describe("personal memory evidence proxy", () => {
  beforeEach(() => {
    getCookie.mockReset();
    vi.restoreAllMocks();
  });

  it("requires authentication without calling the backend", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchMock = vi.spyOn(globalThis, "fetch");

    const response = await GET(new Request("http://localhost"), context("17"));

    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("encodes the record identifier and preserves the evidence response", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const payload = { memory_id: 17, evidence: [{ id: 4 }], missing_evidence_ids: [] };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200 }),
    );

    const response = await GET(new Request("http://localhost"), context("record / 17"));

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/knowledge-memory/record%20%2F%2017/evidence",
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

    const response = await GET(new Request("http://localhost"), context("17"));
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Personal memory evidence service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("internal-backend");
    expect(JSON.stringify(body)).not.toContain("session-value");
  });
});
