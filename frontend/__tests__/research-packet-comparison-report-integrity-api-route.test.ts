import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();
vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

const { POST } = await import(
  "../app/api/research-packet-comparison-report-integrity/route"
);

const requestWithBody = (body = '{"report":"sample"}') =>
  new Request("http://localhost/api/research-packet-comparison-report-integrity", {
    method: "POST",
    body,
    headers: { "content-type": "application/json" },
  });

describe("research packet comparison report integrity proxy", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    getCookie.mockReset();
  });

  it("returns 401 without a session", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const response = await POST(requestWithBody());

    expect(response.status).toBe(401);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("forwards the request and preserves upstream response metadata", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("verified", {
        status: 202,
        headers: { "content-type": "text/plain" },
      }),
    );

    const response = await POST(requestWithBody('{"report":"verified"}'));

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/v1/research-packet-comparison-report-integrity/verify",
      expect.objectContaining({
        method: "POST",
        body: '{"report":"verified"}',
        cache: "no-store",
        headers: {
          "content-type": "application/json",
          authorization: "Bearer session-token",
        },
      }),
    );
    expect(response.status).toBe(202);
    expect(response.headers.get("content-type")).toContain("text/plain");
    expect(await response.text()).toBe("verified");
  });

  it("uses JSON content type when upstream omits it", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("{}", { status: 200 }),
    );

    const response = await POST(requestWithBody());

    expect(response.headers.get("content-type")).toContain("application/json");
  });

  it("returns a controlled 503 when reading the request body fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const request = requestWithBody();
    vi.spyOn(request, "text").mockRejectedValue(new Error("body failure"));
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const response = await POST(request);

    expect(response.status).toBe(503);
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(await response.json()).toEqual({
      detail: "Comparison report integrity service is temporarily unavailable",
    });
  });

  it("returns a controlled 503 when the backend request fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("backend failure"));

    const response = await POST(requestWithBody());

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      detail: "Comparison report integrity service is temporarily unavailable",
    });
  });

  it("returns a controlled 503 when the upstream body cannot be read", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      text: vi.fn().mockRejectedValue(new Error("stream failure")),
    } as unknown as Response);

    const response = await POST(requestWithBody());

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      detail: "Comparison report integrity service is temporarily unavailable",
    });
  });
});
