import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
const unavailableResponse = () =>
  NextResponse.json({ detail: "Research evidence audit packet service unavailable" }, { status: 503 });

export async function POST(request: Request) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  let packet: unknown;
  try {
    packet = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON packet" }, { status: 400 });
  }

  let response: Response;
  try {
    response = await fetch(`${backendUrl}/api/v1/research-evidence-audit/audit-packet/verify`, {
      method: "POST",
      headers: {
        authorization: `Bearer ${token}`,
        "content-type": "application/json",
      },
      body: JSON.stringify(packet),
      cache: "no-store",
    });
  } catch {
    return unavailableResponse();
  }

  let body: string;
  try {
    body = await response.text();
  } catch {
    return unavailableResponse();
  }

  return new NextResponse(body, {
    status: response.status,
    headers: { "content-type": "application/json" },
  });
}
