import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();
vi.mock("next/headers", () => ({ cookies: vi.fn(async () => ({ get: getCookie })) }));

import { GET } from "@/app/api/personal-memory/evidence-remediation/escalations/route";

describe("personal memory remediation escalation proxy", () => {
  beforeEach(() => {
    getCookie.mockReset();
    vi.restoreAllMocks();
  });

  it("requires authentication", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const response = await GET(new Request("http://localhost/api/personal-memory/evidence-remediation/escalations"));
    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("forwards supported filters and preserves the response", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const payload = { total: 1, items: [{ follow_up_id: 9, escalation_state: "critical" }] };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));

    const response = await GET(new Request("http://localhost/api/personal-memory/evidence-remediation/escalations?project_id=7&escalation_state=critical&ignored=yes"));

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/knowledge-memory/evidence-remediation/escalations?project_id=7&escalation_state=critical",
      { method: "GET", headers: { authorization: "Bearer session-value" }, cache: "no-store" },
    );
    expect(await response.json()).toEqual(payload);
  });

  it("returns a stable secret-safe unavailable response", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("internal session-value"));
    const response = await GET(new Request("http://localhost/api/personal-memory/evidence-remediation/escalations"));
    const body = await response.json();
    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Evidence remediation escalation service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("session-value");
  });
});
