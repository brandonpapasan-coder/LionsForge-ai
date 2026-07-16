import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

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

  const response = await fetch(`${backendUrl}/api/v1/research-evidence-audit/audit-packet/verify`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${token}`,
      "content-type": "application/json",
    },
    body: JSON.stringify(packet),
    cache: "no-store",
  });

  return new NextResponse(await response.text(), {
    status: response.status,
    headers: { "content-type": "application/json" },
  });
}
