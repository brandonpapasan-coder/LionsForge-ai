import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(_: NextRequest, context: { params: Promise<{ id: string }> }) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  try {
    const { id } = await context.params;
    const response = await fetch(`${backendUrl}/api/v1/investigations/claims/${id}/summary`, {
      headers: { authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    return new NextResponse(await response.text(), { status: response.status, headers: { "content-type": "application/json" } });
  } catch {
    return NextResponse.json({ detail: "Claim summary service is unavailable" }, { status: 503 });
  }
}
