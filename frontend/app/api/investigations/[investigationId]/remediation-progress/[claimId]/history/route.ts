import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
type RouteContext = { params: Promise<{ investigationId: string; claimId: string }> };

export async function GET(_request: NextRequest, context: RouteContext) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  const { investigationId, claimId } = await context.params;
  try {
    const response = await fetch(
      `${backendUrl}/api/v1/investigations/${investigationId}/remediation-progress/${claimId}/history`,
      { headers: { authorization: `Bearer ${token}` }, cache: "no-store" },
    );
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return NextResponse.json({ detail: "Remediation progress history service is unavailable" }, { status: 503 });
  }
}
