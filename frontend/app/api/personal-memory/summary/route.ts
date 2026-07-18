import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

function unavailable() {
  return NextResponse.json(
    { detail: "Personal memory service is unavailable" },
    { status: 503 },
  );
}

export async function GET(request: Request) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const incomingUrl = new URL(request.url);
  const projectId = incomingUrl.searchParams.get("project_id");
  const target = new URL(`${backendUrl}/api/v1/knowledge-memory/controls/summary`);
  if (projectId) target.searchParams.set("project_id", projectId);

  try {
    const response = await fetch(target, {
      method: "GET",
      headers: { authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return unavailable();
  }
}
