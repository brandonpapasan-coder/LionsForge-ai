import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

async function proxy(request: NextRequest, context: { params: Promise<{ id: string }> }) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  try {
    const { id } = await context.params;
    const response = await fetch(`${backendUrl}/api/v1/investigations/claims/${id}/judgments`, {
      method: request.method,
      headers: {
        authorization: `Bearer ${token}`,
        ...(request.method === "POST" ? { "content-type": "application/json" } : {}),
      },
      body: request.method === "POST" ? await request.text() : undefined,
      cache: "no-store",
    });
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return NextResponse.json({ detail: "Validation ledger service is unavailable" }, { status: 503 });
  }
}

export async function GET(request: NextRequest, context: { params: Promise<{ id: string }> }) {
  return proxy(request, context);
}

export async function POST(request: NextRequest, context: { params: Promise<{ id: string }> }) {
  return proxy(request, context);
}
