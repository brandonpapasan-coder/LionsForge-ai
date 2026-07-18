import { beforeEach, describe, expect, it, vi } from "vitest";

const cookieGet = vi.fn();
vi.mock("next/headers", () => ({ cookies: async () => ({ get: cookieGet }) }));

import { GET } from "@/app/api/release-countdown/route";

describe("release countdown proxy", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    cookieGet.mockReset();
  });

  it("requires a session", async () => {
    cookieGet.mockReturnValue(undefined);
    const response = await GET();
    expect(response.status).toBe(401);
  });

  it("forwards the authenticated request to the backend", async () => {
    cookieGet.mockReturnValue({ value: "session-token" });
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ overall_completion_percent: 90 }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const response = await GET();

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/release-countdown",
      expect.objectContaining({ headers: { authorization: "Bearer session-token" }, cache: "no-store" }),
    );
  });
});
