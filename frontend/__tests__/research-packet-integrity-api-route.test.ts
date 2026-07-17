import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { POST } from "@/app/api/research-packet-integrity/route";

describe("research packet integrity API route", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    getCookie.mockReset();
  });

  it("returns 401 without a session", async () => {
    getCookie.mockReturnValue(undefined);
    const request = { text: vi.fn() } as unknown as Request;
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const response = await POST(request);

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ detail: "Not authenticated" });
    expect(request.text).not.toHaveBeenCalled();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("forwards the request and preserves the upstream response", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const request = { text: vi.fn().mockResolvedValue('{"packet":"value"}') } as unknown as Request;
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"valid":true}', { status: 202 }),
    );

    const response = await POST(request);

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/research-packet-integrity/verify",
      {
        method: "POST",
        headers: {
          authorization: "Bearer session-token",
          "content-type": "application/json",
        },
        body: '{"packet":"value"}',
        cache: "no-store",
      },
    );
    expect(response.status).toBe(202);
    await expect(response.json()).resolves.toEqual({ valid: true });
  });

  it("preserves upstream errors", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const request = { text: vi.fn().mockResolvedValue("{}") } as unknown as Request;
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"detail":"invalid packet"}', { status: 422 }),
    );

    const response = await POST(request);

    expect(response.status).toBe(422);
    await expect(response.json()).resolves.toEqual({ detail: "invalid packet" });
  });

  it("returns 400 when reading the request body fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const request = { text: vi.fn().mockRejectedValue(new Error("request read failed")) } as unknown as Request;
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const response = await POST(request);

    expect(response.status).toBe(400);
    await expect(response.json()).resolves.toEqual({ detail: "Invalid request body" });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("returns 503 when the backend request fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const request = { text: vi.fn().mockResolvedValue("{}") } as unknown as Request;
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("backend request failed"));

    const response = await POST(request);

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Research packet integrity service is unavailable",
    });
  });

  it("returns 503 when reading the upstream body fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const request = { text: vi.fn().mockResolvedValue("{}") } as unknown as Request;
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      text: vi.fn().mockRejectedValue(new Error("response read failed")),
    } as unknown as Response);

    const response = await POST(request);

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Research packet integrity service is unavailable",
    });
  });
});
