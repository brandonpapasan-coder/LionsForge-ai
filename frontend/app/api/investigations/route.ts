import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

async function proxy(method: "GET" | "POST", request?: NextRequest) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  try {
    const response = await fetch(`${backendUrl}/api/v1/investigations`, {
      method,
      headers: {
        authorization: `Bearer ${token}`,
        ...(method === "POST" ? { "content-type": "application/json" } : {}),
      },
      body: method === "POST" && request ? await request.text() : undefined,
      cache: "no-store",
    });
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return NextResponse.json({ detail: "Research workspace is unavailable" }, { status: 503 });
  }
}

export async function GET() {
  return proxy("GET");
}

export async function POST(request: NextRequest) {
  return proxy("POST", request);
}
