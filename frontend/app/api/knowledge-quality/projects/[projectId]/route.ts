import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
const unavailableResponse = { detail: "Knowledge quality service is unavailable" };

type RouteContext = { params: Promise<{ projectId: string }> };

export async function GET(_request: Request, context: RouteContext) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const { projectId } = await context.params;
  if (!/^\d+$/.test(projectId)) {
    return NextResponse.json({ detail: "Research project not found" }, { status: 404 });
  }

  try {
    const response = await fetch(
      `${backendUrl}/api/v1/knowledge-quality/projects/${projectId}`,
      {
        headers: { authorization: `Bearer ${token}` },
        cache: "no-store",
      },
    );

    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return NextResponse.json(unavailableResponse, { status: 503 });
  }
}
