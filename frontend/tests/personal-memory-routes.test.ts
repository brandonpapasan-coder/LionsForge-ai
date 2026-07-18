import { beforeEach, describe, expect, it, vi } from "vitest";

const getCookie = vi.fn();

vi.mock("next/headers", () => ({
  cookies: vi.fn(async () => ({ get: getCookie })),
}));

import { GET as getSummary } from "@/app/api/personal-memory/summary/route";
import { DELETE, GET } from "@/app/api/personal-memory/[memoryId]/route";
import { POST } from "@/app/api/personal-memory/[memoryId]/[action]/route";
import { POST as recoverVersion } from "@/app/api/personal-memory/[memoryId]/recover/[revisionId]/route";

const memoryContext = (memoryId: string) => ({ params: Promise.resolve({ memoryId }) });
const actionContext = (memoryId: string, action: string) => ({
  params: Promise.resolve({ memoryId, action }),
});
const recoveryContext = (memoryId: string, revisionId: string) => ({
  params: Promise.resolve({ memoryId, revisionId }),
});

describe("personal memory API proxies", () => {
  beforeEach(() => {
    getCookie.mockReset();
    vi.restoreAllMocks();
  });

  it("requires authentication without calling the backend", async () => {
    getCookie.mockReturnValue(undefined);
    const fetchMock = vi.spyOn(globalThis, "fetch");

    const response = await getSummary(new Request("http://localhost/api/personal-memory/summary"));

    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("forwards summary project scope with no-store", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ total_count: 2 }), { status: 200 }),
    );

    const response = await getSummary(
      new Request("http://localhost/api/personal-memory/summary?project_id=project / alpha"),
    );

    const [target, init] = fetchMock.mock.calls[0];
    expect(String(target)).toBe(
      "http://localhost:8000/api/v1/knowledge-memory/controls/summary?project_id=project+%2F+alpha",
    );
    expect(init).toEqual({
      method: "GET",
      headers: { authorization: "Bearer session-value" },
      cache: "no-store",
    });
    expect(response.status).toBe(200);
  });

  it("encodes memory identifiers and preserves upstream bodies", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "memory / 1" }), { status: 200 }),
    );

    const response = await GET(new Request("http://localhost"), memoryContext("memory / 1"));

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/knowledge-memory/memory%20%2F%201",
      {
        method: "GET",
        headers: { authorization: "Bearer session-value" },
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
  });

  it("preserves 204 deletion responses", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }));

    const response = await DELETE(new Request("http://localhost"), memoryContext("17"));

    expect(response.status).toBe(204);
    expect(await response.text()).toBe("");
  });

  it("allows archive and restore actions and rejects unsupported actions", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ status: "archived" }), { status: 200 }),
    );

    const archived = await POST(
      new Request("http://localhost", { method: "POST" }),
      actionContext("17", "archive"),
    );
    expect(archived.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/knowledge-memory/17/archive",
      {
        method: "POST",
        headers: { authorization: "Bearer session-value" },
        cache: "no-store",
      },
    );

    const rejected = await POST(
      new Request("http://localhost", { method: "POST" }),
      actionContext("17", "validate"),
    );
    expect(rejected.status).toBe(404);
  });

  it("encodes record and version identifiers for recovery", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ revision_number: 4 }), { status: 200 }),
    );

    const response = await recoverVersion(
      new Request("http://localhost", { method: "POST" }),
      recoveryContext("record / 17", "version / 2"),
    );

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/knowledge-memory/record%20%2F%2017/recover/version%20%2F%202",
      {
        method: "POST",
        headers: { authorization: "Bearer session-value" },
        cache: "no-store",
      },
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ revision_number: 4 });
  });

  it("returns stable secret-safe 503 responses", async () => {
    getCookie.mockReturnValue({ value: "session-value" });
    vi.spyOn(globalThis, "fetch").mockRejectedValue(
      new Error("http://internal-backend failed with session-value"),
    );

    const response = await GET(new Request("http://localhost"), memoryContext("17"));
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body).toEqual({ detail: "Personal memory service is unavailable" });
    expect(JSON.stringify(body)).not.toContain("internal-backend");
    expect(JSON.stringify(body)).not.toContain("session-value");
  });
});
