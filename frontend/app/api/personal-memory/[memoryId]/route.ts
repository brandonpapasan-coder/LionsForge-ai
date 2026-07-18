import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

function unavailable() {
  return NextResponse.json(
    { detail: "Personal memory service is unavailable" },
    { status: 503 },
  );
}

async function proxy(
  method: "GET" | "DELETE",
  context: { params: Promise<{ memoryId: string }> },
) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const { memoryId } = await context.params;
  try {
    const response = await fetch(
      `${backendUrl}/api/v1/knowledge-memory/${encodeURIComponent(memoryId)}`,
      {
        method,
        headers: { authorization: `Bearer ${token}` },
        cache: "no-store",
      },
    );
    if (response.status === 204) return new NextResponse(null, { status: 204 });
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return unavailable();
  }
}

export async function GET(
  _request: Request,
  context: { params: Promise<{ memoryId: string }> },
) {
  return proxy("GET", context);
}

export async function DELETE(
  _request: Request,
  context: { params: Promise<{ memoryId: string }> },
) {
  return proxy("DELETE", context);
}
