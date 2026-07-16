import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  let payload: unknown;
  try { payload = await request.json(); } catch { return NextResponse.json({ detail: "Invalid JSON payload" }, { status: 400 }); }
  const response = await fetch(`${backendUrl}/api/v1/research-evidence-audit/review-actions/generate`, {
    method: "POST",
    headers: { authorization: `Bearer ${token}`, "content-type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  return new NextResponse(await response.text(), { status: response.status, headers: { "content-type": "application/json" } });
}
