import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

type RouteContext = { params: Promise<{ projectId: string }> };

export async function GET(_request: Request, context: RouteContext) {
  const cookieStore = await cookies();
  const session = cookieStore.get("lionsforge_session")?.value;
  if (!session) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const { projectId } = await context.params;
  if (!/^\d+$/.test(projectId)) {
    return NextResponse.json({ detail: "Research project not found" }, { status: 404 });
  }

  try {
    const response = await fetch(
      `${backendUrl}/api/v1/research-trust-index/projects/${projectId}`,
      {
        headers: { authorization: `Bearer ${session}` },
        cache: "no-store",
      },
    );

    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return NextResponse.json(
      { detail: "Research trust service is unavailable" },
      { status: 503 },
    );
  }
}
