import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";

function unavailableResponse() {
  return NextResponse.json(
    { detail: "Comparison report export service is temporarily unavailable" },
    { status: 503 },
  );
}

function invalidBodyResponse() {
  return NextResponse.json(
    { detail: "Invalid request body" },
    { status: 400 },
  );
}

export async function POST(request: Request) {
  const session = (await cookies()).get("lionsforge_session")?.value;
  if (!session) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  let body: string;
  try {
    body = await request.text();
  } catch {
    return invalidBodyResponse();
  }

  let response: Response;
  try {
    response = await fetch(`${BACKEND_URL}/api/v1/research-packet-comparison-report/export`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${session}`,
      },
      body,
      cache: "no-store",
    });
  } catch {
    return unavailableResponse();
  }

  let responseBody: string;
  try {
    responseBody = await response.text();
  } catch {
    return unavailableResponse();
  }

  return new NextResponse(responseBody, {
    status: response.status,
    headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
  });
}
