import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

async function proxy(request: Request, projectId: string) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  const response = await fetch(`${backendUrl}/api/v1/research-conclusions/projects/${encodeURIComponent(projectId)}`, {
    method: request.method,
    headers: { authorization: `Bearer ${token}`, "content-type": "application/json" },
    body: request.method === "GET" ? undefined : await request.text(),
    cache: "no-store",
  });
  return new NextResponse(await response.text(), { status: response.status, headers: { "content-type": "application/json" } });
}

export async function GET(request: Request, context: { params: Promise<{ projectId: string }> }) {
  return proxy(request, (await context.params).projectId);
}

export async function PUT(request: Request, context: { params: Promise<{ projectId: string }> }) {
  return proxy(request, (await context.params).projectId);
}
