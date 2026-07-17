import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(
  request: Request,
  context: { params: Promise<{ projectId: string }> },
) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const { projectId } = await context.params;
  const rawDays = new URL(request.url).searchParams.get("days") ?? "30";
  if (!/^\d+$/.test(rawDays)) {
    return NextResponse.json({ detail: "Invalid days value" }, { status: 400 });
  }

  const days = Number(rawDays);
  if (days < 1 || days > 365) {
    return NextResponse.json({ detail: "Invalid days value" }, { status: 400 });
  }

  try {
    const response = await fetch(
      `${backendUrl}/api/v1/research-governance-dashboard/projects/${encodeURIComponent(projectId)}?days=${days}`,
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
    return NextResponse.json(
      { detail: "Research governance service is unavailable" },
      { status: 503 },
    );
  }
}
