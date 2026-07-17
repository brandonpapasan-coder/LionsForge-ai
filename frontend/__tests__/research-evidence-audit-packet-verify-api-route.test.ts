import { beforeEach, describe, expect, it, vi } from "vitest";

const cookiesMock = vi.fn();

vi.mock("next/headers", () => ({
  cookies: cookiesMock,
}));

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
    vi.restoreAllMocks();
    cookiesMock.mockReset();
  });

  it("returns 401 without authentication", async () => {
    cookiesMock.mockResolvedValue({ get: vi.fn().mockReturnValue(undefined) });
    const fetchMock = vi.spyOn(globalThis, "fetch");

    const response = await POST(request("{}"));

    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns 400 for invalid JSON", async () => {
    cookiesMock.mockResolvedValue({ get: vi.fn().mockReturnValue({ value: "session-token" }) });
    const fetchMock = vi.spyOn(globalThis, "fetch");

    const response = await POST(request("{"));

    expect(response.status).toBe(400);
    await expect(response.json()).resolves.toEqual({ detail: "Invalid JSON packet" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("forwards the packet and preserves upstream response", async () => {
    cookiesMock.mockResolvedValue({ get: vi.fn().mockReturnValue({ value: "session-token" }) });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"valid":true}', {
        status: 202,
        headers: { "content-type": "application/json" },
      }),
    );

    const response = await POST(request('{"packetId":"p1"}'));

    expect(fetchMock).toHaveBeenCalledWith(
      "http://backend:8000/api/v1/research-evidence-audit/audit-packet/verify",
      {
        method: "POST",
        headers: { authorization: "Bearer session-token", "content-type": "application/json" },
        body: JSON.stringify({ packetId: "p1" }),
        cache: "no-store",
      },
    );
    expect(response.status).toBe(202);
    expect(response.headers.get("content-type")).toContain("application/json");
    await expect(response.text()).resolves.toBe('{"valid":true}');
  });

  it("returns 503 when the backend request fails", async () => {
    cookiesMock.mockResolvedValue({ get: vi.fn().mockReturnValue({ value: "session-token" }) });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("offline"));

    const response = await POST(request("{}"));

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Research evidence audit packet service unavailable",
    });
  });

  it("returns 503 when the upstream body cannot be read", async () => {
    cookiesMock.mockResolvedValue({ get: vi.fn().mockReturnValue({ value: "session-token" }) });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      text: vi.fn().mockRejectedValue(new Error("read failed")),
    } as unknown as Response);

    const response = await POST(request("{}"));

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Research evidence audit packet service unavailable",
    });
  });
});
