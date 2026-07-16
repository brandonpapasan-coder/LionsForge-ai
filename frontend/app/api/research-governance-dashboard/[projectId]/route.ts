import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(request: Request, context: { params: Promise<{ projectId: string }> }) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  const { projectId } = await context.params;
  const days = new URL(request.url).searchParams.get("days") ?? "30";
  const response = await fetch(`${backendUrl}/api/v1/research-governance-dashboard/projects/${projectId}?days=${encodeURIComponent(days)}`, {
    headers: { authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  return new NextResponse(await response.text(), { status: response.status, headers: { "content-type": "application/json" } });
}
