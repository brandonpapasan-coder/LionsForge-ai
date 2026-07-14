import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

async function sessionToken() {
  const cookieStore = await cookies();
  return cookieStore.get("lionsforge_session")?.value;
}

export async function GET() {
  const token = await sessionToken();
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  const response = await fetch(`${backendUrl}/api/v1/education/assessment`, {
    headers: { authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  return new NextResponse(await response.text(), {
    status: response.status,
    headers: { "content-type": "application/json" },
  });
}

export async function POST(request: NextRequest) {
  const token = await sessionToken();
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  const response = await fetch(`${backendUrl}/api/v1/education/assessment`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${token}`,
      "content-type": "application/json",
    },
    body: await request.text(),
  });
  return new NextResponse(await response.text(), {
    status: response.status,
    headers: { "content-type": "application/json" },
  });
}
