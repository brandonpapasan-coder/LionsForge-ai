import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

async function sessionToken() {
  const cookieStore = await cookies();
  return cookieStore.get("lionsforge_session")?.value;
}

async function proxyAssessment(request?: NextRequest) {
  const token = await sessionToken();
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  try {
    const response = await fetch(`${backendUrl}/api/v1/education/assessment`, {
      method: request ? "POST" : "GET",
      headers: request
        ? {
            authorization: `Bearer ${token}`,
            "content-type": "application/json",
          }
        : { authorization: `Bearer ${token}` },
      body: request ? await request.text() : undefined,
      cache: "no-store",
    });

    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return NextResponse.json(
      { detail: "Education assessment service is unavailable" },
      { status: 503 },
    );
  }
}

export async function GET() {
  return proxyAssessment();
}

export async function POST(request: NextRequest) {
  return proxyAssessment(request);
}
