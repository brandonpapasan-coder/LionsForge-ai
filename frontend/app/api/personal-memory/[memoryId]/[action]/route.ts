import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
const supportedActions = new Set(["archive", "restore"]);

function unavailable() {
  return NextResponse.json(
    { detail: "Personal memory service is unavailable" },
    { status: 503 },
  );
}

export async function POST(
  _request: Request,
  context: { params: Promise<{ memoryId: string; action: string }> },
) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const { memoryId, action } = await context.params;
  if (!supportedActions.has(action)) {
    return NextResponse.json({ detail: "Unsupported memory action" }, { status: 404 });
  }

  try {
    const response = await fetch(
      `${backendUrl}/api/v1/knowledge-memory/${encodeURIComponent(memoryId)}/${action}`,
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
    return unavailable();
  }
}
