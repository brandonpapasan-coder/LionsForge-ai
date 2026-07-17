import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
const unavailableDetail = "Research conclusion workspace service unavailable";

async function proxy(request: Request, projectId: string) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  let body: string | undefined;
  if (request.method !== "GET") {
    try {
      body = await request.text();
    } catch {
      return NextResponse.json({ detail: "Invalid request body" }, { status: 400 });
    }
  }

  let response: Response;
  try {
    response = await fetch(`${backendUrl}/api/v1/research-conclusions/projects/${encodeURIComponent(projectId)}`, {
      method: request.method,
      headers: { authorization: `Bearer ${token}`, "content-type": "application/json" },
      body,
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ detail: unavailableDetail }, { status: 503 });
  }

  let responseBody: string;
  try {
    responseBody = await response.text();
  } catch {
    return NextResponse.json({ detail: unavailableDetail }, { status: 503 });
  }

  return new NextResponse(responseBody, {
    status: response.status,
    headers: { "content-type": "application/json" },
  });
}

export async function GET(request: Request, context: { params: Promise<{ projectId: string }> }) {
  return proxy(request, (await context.params).projectId);
}

export async function PUT(request: Request, context: { params: Promise<{ projectId: string }> }) {
  return proxy(request, (await context.params).projectId);
}
