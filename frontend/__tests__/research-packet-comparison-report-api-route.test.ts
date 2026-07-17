import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { POST } from "@/app/api/research-packet-comparison-report/route";

describe("research packet comparison report API route", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    getCookie.mockReset();
  });

  it("returns 401 without a session and does not call the backend", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const response = await POST(new Request("http://localhost/api", { method: "POST", body: "{}" }));

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ detail: "Not authenticated" });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("forwards the request and preserves upstream status, body, and content type", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("report-body", {
        status: 206,
        headers: { "content-type": "application/pdf" },
      }),
    );

    const response = await POST(
      new Request("http://localhost/api", { method: "POST", body: JSON.stringify({ report: "x" }) }),
    );

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/v1/research-packet-comparison-report/export",
      {
        method: "POST",
        headers: {
          "content-type": "application/json",
          authorization: "Bearer session-token",
        },
        body: JSON.stringify({ report: "x" }),
        cache: "no-store",
      },
    );
    expect(response.status).toBe(206);
    expect(response.headers.get("content-type")).toBe("application/pdf");
    await expect(response.text()).resolves.toBe("report-body");
  });

  it("preserves an upstream error response", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "invalid report" }), {
        status: 422,
        headers: { "content-type": "application/problem+json" },
      }),
    );

    const response = await POST(new Request("http://localhost/api", { method: "POST", body: "{}" }));

    expect(response.status).toBe(422);
    expect(response.headers.get("content-type")).toBe("application/problem+json");
    await expect(response.json()).resolves.toEqual({ detail: "invalid report" });
  });

  it("returns a stable 503 when reading the request body fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const request = { text: vi.fn().mockRejectedValue(new Error("request read failed")) } as unknown as Request;

    const response = await POST(request);

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Comparison report export service is temporarily unavailable",
    });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("returns a stable 503 when the backend connection fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("connection failed"));

    const response = await POST(new Request("http://localhost/api", { method: "POST", body: "{}" }));

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Comparison report export service is temporarily unavailable",
    });
  });

  it("returns a stable 503 when reading the upstream body fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      text: vi.fn().mockRejectedValue(new Error("response read failed")),
    } as unknown as Response);

    const response = await POST(new Request("http://localhost/api", { method: "POST", body: "{}" }));

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Comparison report export service is temporarily unavailable",
    });
  });
});
