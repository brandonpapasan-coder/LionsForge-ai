import { beforeEach, describe, expect, it, vi } from "vitest";

const cookieGet = vi.fn();
vi.mock("next/headers", () => ({ cookies: async () => ({ get: cookieGet }) }));

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

process.env.BACKEND_URL = "http://backend:8000";
const { POST } = await import("../app/api/research-evidence-audit-packet/verify/route");

const request = (body: string) =>
  new Request("http://localhost/api/research-evidence-audit-packet/verify", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body,
  });

describe("audit packet verification API route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    cookieGet.mockReturnValue({ value: "session-token" });
  });

  it("returns 401 without authentication", async () => {
    cookieGet.mockReturnValue(undefined);
    const response = await POST(request("{}"));
    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns 400 for invalid JSON", async () => {
    const response = await POST(request("{"));
    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ detail: "Invalid JSON packet" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("forwards the packet and preserves upstream response", async () => {
    fetchMock.mockResolvedValue(new Response('{"valid":true}', { status: 202 }));
    const response = await POST(request('{"packetId":"p1"}'));
    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend:8000/api/v1/research-evidence-audit/audit-packet/verify",
      expect.objectContaining({
        method: "POST",
        headers: { authorization: "Bearer session-token", "content-type": "application/json" },
        body: JSON.stringify({ packetId: "p1" }),
        cache: "no-store",
      }),
    );
    expect(response.status).toBe(202);
    expect(await response.text()).toBe('{"valid":true}');
    expect(response.headers.get("content-type")).toContain("application/json");
  });

  it("returns 503 when the backend request fails", async () => {
    fetchMock.mockRejectedValue(new Error("offline"));
    const response = await POST(request("{}"));
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ detail: "Research evidence audit packet service unavailable" });
  });

  it("returns 503 when the upstream body cannot be read", async () => {
    fetchMock.mockResolvedValue({ status: 200, text: vi.fn().mockRejectedValue(new Error("read failed")) });
    const response = await POST(request("{}"));
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ detail: "Research evidence audit packet service unavailable" });
  });
});
