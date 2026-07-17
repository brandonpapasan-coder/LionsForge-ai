import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();
vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

const { GET } = await import(
  "../app/api/research-evidence-provenance/ledger/route"
);

const request = (suffix = "") =>
  new Request(`http://localhost/api/research-evidence-provenance/ledger${suffix}`);

describe("research evidence provenance ledger proxy", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    getCookie.mockReset();
  });

  it("returns 401 without a session", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const response = await GET(request());

    expect(response.status).toBe(401);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("forwards requests without a project filter", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"entries":[]}', { status: 200 }),
    );

    const response = await GET(request());

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/research-evidence-provenance/ledger",
      {
        headers: { authorization: "Bearer session-token" },
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("application/json");
    expect(await response.text()).toBe('{"entries":[]}');
  });

  it("encodes and forwards the optional project filter", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response('{"entries":[1]}', { status: 206 }),
    );

    const response = await GET(request("?project_id=alpha%20beta%2Fgamma"));

    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/research-evidence-provenance/ledger?project_id=alpha%20beta%2Fgamma",
      expect.any(Object),
    );
    expect(response.status).toBe(206);
    expect(await response.text()).toBe('{"entries":[1]}');
  });

  it("returns a controlled 503 when the backend request fails", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("backend failure"));

    const response = await GET(request());

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      detail: "Evidence provenance ledger service is temporarily unavailable",
    });
  });

  it("returns a controlled 503 when the upstream body cannot be read", async () => {
    getCookie.mockReturnValue({ value: "session-token" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      status: 200,
      text: vi.fn().mockRejectedValue(new Error("stream failure")),
    } as unknown as Response);

    const response = await GET(request());

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      detail: "Evidence provenance ledger service is temporarily unavailable",
    });
  });
});
