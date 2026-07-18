import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

async function sessionToken() {
  const cookieStore = await cookies();
  return cookieStore.get("lionsforge_session")?.value;
}

function unavailable() {
  return NextResponse.json(
    { detail: "Education assessment service is unavailable" },
    { status: 503 },
  );
}

function invalidRequestBody() {
  return NextResponse.json({ detail: "Invalid request body" }, { status: 400 });
}

async function proxyAssessment(request?: NextRequest) {
  const token = await sessionToken();
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  let body: string | undefined;
  if (request) {
    try {
      body = await request.text();
    } catch {
      return invalidRequestBody();
    }
  }

  let response: Response;
  try {
    response = await fetch(`${backendUrl}/api/v1/education/assessment`, {
      method: request ? "POST" : "GET",
      headers: request
        ? {
            authorization: `Bearer ${token}`,
            "content-type": "application/json",
          }
        : { authorization: `Bearer ${token}` },
      body,
      cache: "no-store",
    });
  } catch {
    return unavailable();
  }

  let responseBody: string;
  try {
    responseBody = await response.text();
  } catch {
    return unavailable();
  }

  return new NextResponse(responseBody, {
    status: response.status,
    headers: { "content-type": "application/json" },
  });
}

export async function GET() {
  return proxyAssessment();
}

export async function POST(request: NextRequest) {
  return proxyAssessment(request);
}
