import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
type RouteContext = { params: Promise<{ investigationId: string }> };

async function proxy(method: "GET" | "PUT", request: NextRequest | undefined, context: RouteContext) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  const { investigationId } = await context.params;
  try {
    const response = await fetch(`${backendUrl}/api/v1/investigations/${investigationId}/synthesis`, {
      method,
      headers: { authorization: `Bearer ${token}`, ...(method === "PUT" ? { "content-type": "application/json" } : {}) },
      body: method === "PUT" && request ? await request.text() : undefined,
      cache: "no-store",
    });
    return new NextResponse(await response.text(), { status: response.status, headers: { "content-type": "application/json" } });
  } catch { return NextResponse.json({ detail: "Research workspace is unavailable" }, { status: 503 }); }
}

export async function GET(request: NextRequest, context: RouteContext) { return proxy("GET", request, context); }
export async function PUT(request: NextRequest, context: RouteContext) { return proxy("PUT", request, context); }
