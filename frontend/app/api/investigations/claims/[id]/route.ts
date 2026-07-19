import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

async function proxy(method: "PATCH" | "DELETE", request: NextRequest | undefined, id: string) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  try {
    const response = await fetch(`${backendUrl}/api/v1/investigations/claims/${id}`, {
      method,
      headers: { authorization: `Bearer ${token}`, ...(method === "PATCH" ? { "content-type": "application/json" } : {}) },
      body: method === "PATCH" && request ? await request.text() : undefined,
      cache: "no-store",
    });
    return new NextResponse(await response.text(), { status: response.status, headers: { "content-type": "application/json" } });
  } catch {
    return NextResponse.json({ detail: "Claim service is unavailable" }, { status: 503 });
  }
}

export async function PATCH(request: NextRequest, context: { params: Promise<{ id: string }> }) {
  return proxy("PATCH", request, (await context.params).id);
}

export async function DELETE(_: NextRequest, context: { params: Promise<{ id: string }> }) {
  return proxy("DELETE", undefined, (await context.params).id);
}
