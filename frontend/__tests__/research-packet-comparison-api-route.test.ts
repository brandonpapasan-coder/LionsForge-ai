import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { POST } from "@/app/api/research-packet-comparison/route";

describe("research packet comparison API route", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    getCookie.mockReset();
  });

  it("returns 401 without a session and does not call the backend", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const response = await POST(new Request("http://localhost/api/research-packet-comparison", { method: "POST" }));

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ detail: "Not authenticated" });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("forwards the request and preserves the upstream response", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const payload = JSON.stringify({ packet_ids: ["packet-a", "packet-b"] });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ comparison: "complete" }), { status: 207 }),
    );

    const response = await POST(
      new Request("http://localhost/api/research-packet-comparison", {
        method: "POST",
        body: payload,
      }),
    );

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/research-packet-comparison/compare",
      {
        method: "POST",
        headers: {
          authorization: "Bearer session-token",
          "content-type": "application/json",
        },
        body: payload,
        cache: "no-store",
      },
    );
    expect(response.status).toBe(207);
    await expect(response.json()).resolves.toEqual({ comparison: "complete" });
  });

  it("preserves upstream non-success responses", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "comparison rejected" }), { status: 422 }),
    );

    const response = await POST(
      new Request("http://localhost/api/research-packet-comparison", {
        method: "POST",
        body: "{}",
      }),
    );

    expect(response.status).toBe(422);
    await expect(response.json()).resolves.toEqual({ detail: "comparison rejected" });
  });

  it("returns a stable 503 when reading the request body fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const request = { text: vi.fn().mockRejectedValue(new Error("request read failed")) } as unknown as Request;

    const response = await POST(request);

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Research packet comparison service is temporarily unavailable",
    });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("returns a stable 503 when the backend connection fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("backend unavailable"));

    const response = await POST(
      new Request("http://localhost/api/research-packet-comparison", {
        method: "POST",
        body: "{}",
      }),
    );

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Research packet comparison service is temporarily unavailable",
    });
  });

  it("returns a stable 503 when reading the upstream body fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      text: vi.fn().mockRejectedValue(new Error("response read failed")),
    } as unknown as Response);

    const response = await POST(
      new Request("http://localhost/api/research-packet-comparison", {
        method: "POST",
        body: "{}",
      }),
    );

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Research packet comparison service is temporarily unavailable",
    });
  });
});
