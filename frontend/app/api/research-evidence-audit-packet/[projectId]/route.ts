import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(_request: Request, context: { params: Promise<{ projectId: string }> }) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  const { projectId } = await context.params;
  if (!/^\d+$/.test(projectId)) return NextResponse.json({ detail: "Invalid project" }, { status: 400 });

  let response: Response;
  try {
    response = await fetch(`${backendUrl}/api/v1/research-evidence-audit-packet/${projectId}`, {
      headers: { authorization: `Bearer ${token}` },
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { detail: "Research evidence audit packet service unavailable" },
      { status: 503 },
    );
  }

  let body: string;
  try {
    body = await response.text();
  } catch {
    return NextResponse.json(
      { detail: "Research evidence audit packet response unavailable" },
      { status: 503 },
    );
  }

  return new NextResponse(body, {
    status: response.status,
    headers: { "content-type": "application/json" },
  });
}
