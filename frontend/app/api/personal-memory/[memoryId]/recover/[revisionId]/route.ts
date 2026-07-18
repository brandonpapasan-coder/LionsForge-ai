import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(
  _request: Request,
  context: { params: Promise<{ memoryId: string; revisionId: string }> },
) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const { memoryId, revisionId } = await context.params;
  try {
    const response = await fetch(
      `${backendUrl}/api/v1/knowledge-memory/${encodeURIComponent(memoryId)}/recover/${encodeURIComponent(revisionId)}`,
      {
        method: "POST",
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
      { detail: "Personal memory service is unavailable" },
      { status: 503 },
    );
  }
}
