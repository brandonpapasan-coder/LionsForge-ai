import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

async function proxy(method: "GET" | "POST", request: NextRequest | undefined, id: string) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  try {
    const response = await fetch(`${backendUrl}/api/v1/investigations/${id}/claims`, {
      method,
      headers: { authorization: `Bearer ${token}`, ...(method === "POST" ? { "content-type": "application/json" } : {}) },
      body: method === "POST" && request ? await request.text() : undefined,
      cache: "no-store",
    });
    return new NextResponse(await response.text(), { status: response.status, headers: { "content-type": "application/json" } });
  } catch {
    return NextResponse.json({ detail: "Claim service is unavailable" }, { status: 503 });
  }
}

export async function GET(_: NextRequest, context: { params: Promise<{ id: string }> }) {
  return proxy("GET", undefined, (await context.params).id);
}

export async function POST(request: NextRequest, context: { params: Promise<{ id: string }> }) {
  return proxy("POST", request, (await context.params).id);
}
