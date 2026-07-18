import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(request: Request) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  const incoming = new URL(request.url);
  const params = new URLSearchParams();
  const projectId = incoming.searchParams.get("project_id");
  const escalationState = incoming.searchParams.get("escalation_state");
  if (projectId) params.set("project_id", projectId);
  if (escalationState) params.set("escalation_state", escalationState);
  const suffix = params.size ? `?${params.toString()}` : "";

  try {
    const response = await fetch(
      `${backendUrl}/api/v1/knowledge-memory/evidence-remediation/escalations${suffix}`,
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
      { detail: "Evidence remediation escalation service is unavailable" },
      { status: 503 },
    );
  }
}
