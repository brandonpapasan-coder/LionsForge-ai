import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

async function proxy(
  request: Request,
  context: { params: Promise<{ projectId: string }> },
) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const { projectId } = await context.params;

  try {
    const response = await fetch(
      `${backendUrl}/api/v1/research-projects/${encodeURIComponent(projectId)}/sessions`,
      {
        method: request.method,
        headers: {
          authorization: `Bearer ${token}`,
          "content-type": "application/json",
        },
        body: request.method === "GET" ? undefined : await request.text(),
        cache: "no-store",
      },
    );

    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return NextResponse.json(
      { detail: "Research sessions service is unavailable" },
      { status: 503 },
    );
  }
}

export async function GET(
  request: Request,
  context: { params: Promise<{ projectId: string }> },
) {
  return proxy(request, context);
}

export async function POST(
  request: Request,
  context: { params: Promise<{ projectId: string }> },
) {
  return proxy(request, context);
}
