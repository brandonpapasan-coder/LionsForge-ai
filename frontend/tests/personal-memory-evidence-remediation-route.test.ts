import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();
vi.mock("next/headers", () => ({ cookies: vi.fn(async () => ({ get: getCookie })) }));

import { GET } from "@/app/api/personal-memory/[memoryId]/evidence-remediation/route";
import { POST } from "@/app/api/personal-memory/[memoryId]/evidence-remediation/follow-ups/route";

const context = (memoryId: string) => ({ params: Promise.resolve({ memoryId }) });

describe("personal memory remediation proxies", () => {
  beforeEach(() => {
    getCookie.mockReset();
    vi.restoreAllMocks();
  });

  it("requires authentication before reading or creating remediation items", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchMock = vi.spyOn(globalThis, "fetch");

    expect((await GET(new Request("http://localhost"), context("17"))).status).toBe(401);
    expect((await POST(new Request("http://localhost", { method: "POST", body: "{}" }), context("17"))).status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("encodes the record identifier and preserves remediation responses", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const plan = { memory_id: 17, total_actions: 1, actions: [{ action_key: "key" }] };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(plan), { status: 200 }),
    );

    const response = await GET(new Request("http://localhost"), context("record / 17"));

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/knowledge-memory/record%20%2F%2017/evidence-remediation",
      {
        method: "GET",
        headers: { authorization: "Bearer session-value" },
        cache: "no-store",
      },
    );
    expect(await response.json()).toEqual(plan);
  });

  it("forwards confirmed research remediation creation payloads", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const result = { created: true, follow_up_id: 9, action_key: "key" };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(result), { status: 200 }),
    );
    const payload = JSON.stringify({ action_key: "key", confirmed: true });

    const response = await POST(
      new Request("http://localhost", { method: "POST", body: payload }),
      context("17"),
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/knowledge-memory/17/evidence-remediation/follow-ups",
      {
        method: "POST",
        headers: { authorization: "Bearer session-value", "content-type": "application/json" },
        body: payload,
        cache: "no-store",
      },
    );
    expect(await response.json()).toEqual(result);
  });

  it("returns stable secret-safe unavailable responses", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new Error("http://internal-backend failed with session-value"),
    );

    const response = await GET(new Request("http://localhost"), context("17"));
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Personal memory remediation service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("internal-backend");
    expect(JSON.stringify(body)).not.toContain("session-value");
  });
});
