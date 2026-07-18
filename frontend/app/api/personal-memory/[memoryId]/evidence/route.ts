import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(
  _request: Request,
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
      `${backendUrl}/api/v1/knowledge-memory/${encodeURIComponent(memoryId)}/evidence`,
      {
        method: "GET",
        headers: { authorization: `Bearer ${token}` },
        cache: "no-store",
      },
    );
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return NextResponse.json(
      { detail: "Personal memory evidence service is unavailable" },
      { status: 503 },
    );
  }
}
