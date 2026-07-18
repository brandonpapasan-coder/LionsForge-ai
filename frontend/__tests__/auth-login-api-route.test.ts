import { beforeEach, describe, expect, it, vi } from "vitest";

import { POST } from "@/app/api/auth/login/route";

describe("auth login API proxy", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns 400 when reading the request body fails", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    const request = {
      text: vi.fn().mockRejectedValue(new Error("secret request read failure")),
    } as unknown as Request;

    const response = await POST(request);
    const body = await response.json();

    expect(response.status).toBe(400);
    expect(body).toEqual({ detail: "Invalid request body" });
    expect(JSON.stringify(body)).not.toContain("secret request read failure");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns a stable 503 when the backend fetch fails", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new Error("http://internal-backend:8000 failed with credentials"),
    );

    const response = await POST(
      new Request("http://localhost/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: "user@example.com", password: "secret" }),
      }),
    );
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Authentication service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("internal-backend");
    expect(JSON.stringify(body)).not.toContain("secret");
  });

  it("returns a stable 503 when the upstream response cannot be parsed", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      json: vi.fn().mockRejectedValue(new Error("invalid upstream payload")),
    } as unknown as Response);

    const response = await POST(
      new Request("http://localhost/api/auth/login", {
        method: "POST",
        body: "{}",
      }),
    );

    expect(response.status).toBe(503);
    await expect(response.json()).resolves.toEqual({
      detail: "Authentication service is unavailable",
    });
  });

  it("preserves an upstream authentication error status and body", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Invalid credentials" }), { status: 401 }),
    );

    const response = await POST(
      new Request("http://localhost/api/auth/login", {
        method: "POST",
        body: "{}",
      }),
    );

    expect(response.status).toBe(401);
    await expect(response.json()).resolves.toEqual({ detail: "Invalid credentials" });
  });

  it("forwards the body and sets the session cookie after a successful login", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ access_token: "access-token" }), { status: 200 }),
    );
    const requestBody = JSON.stringify({ email: "user@example.com", password: "secret" });

    const response = await POST(
      new Request("http://localhost/api/auth/login", {
        method: "POST",
        body: requestBody,
      }),
    );

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/v1/auth/login", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: requestBody,
      cache: "no-store",
    });
    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ ok: true });
    expect(response.headers.get("set-cookie")).toContain("lionsforge_session=access-token");
    expect(response.headers.get("set-cookie")).toContain("HttpOnly");
    expect(response.headers.get("set-cookie")).toContain("SameSite=lax");
  });
});
