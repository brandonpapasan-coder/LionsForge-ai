import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();
vi.mock("next/headers", () => ({ cookies: vi.fn(async () => ({ get: getCookie })) }));

import { GET } from "@/app/api/personal-memory/[memoryId]/evidence-remediation/verification/route";
import { POST } from "@/app/api/personal-memory/[memoryId]/evidence-remediation/verification/resolve/route";

const context = (memoryId: string) => ({ params: Promise.resolve({ memoryId }) });

describe("personal memory remediation verification proxies", () => {
  beforeEach(() => {
    getCookie.mockReset();
    vi.restoreAllMocks();
  });

  it("requires authentication before verification or resolution", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchMock = vi.spyOn(globalThis, "fetch");
    expect((await GET(new Request("http://localhost"), context("17"))).status).toBe(401);
    expect((await POST(new Request("http://localhost", { method: "POST", body: "{}" }), context("17"))).status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("encodes identifiers and preserves verification responses", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const payload = { memory_id: 17, ready_for_resolution_count: 1, actions: [] };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
    const response = await GET(new Request("http://localhost"), context("record / 17"));
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/knowledge-memory/record%20%2F%2017/evidence-remediation/verification",
      { method: "GET", headers: { authorization: "Bearer session-value" }, cache: "no-store" },
    );
    expect(await response.json()).toEqual(payload);
  });

  it("forwards confirmed resolution notes", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const result = { resolved: true, follow_up_id: 44, status: "resolved" };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(result), { status: 200 }));
    const payload = JSON.stringify({ action_key: "key", confirmed: true, resolution_notes: "Verified." });
    const response = await POST(new Request("http://localhost", { method: "POST", body: payload }), context("17"));
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/knowledge-memory/17/evidence-remediation/verification/resolve",
      {
        method: "POST",
        headers: { authorization: "Bearer session-value", "content-type": "application/json" },
        body: payload,
        cache: "no-store",
      },
    );
    expect(await response.json()).toEqual(result);
  });

  it("returns secret-safe unavailable responses", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("internal-backend session-value"));
    const response = await GET(new Request("http://localhost"), context("17"));
    const body = await response.json();
    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Personal memory remediation verification service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("session-value");
  });
});
