import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
const unavailableResponse = () =>
  NextResponse.json(
    { detail: "Research packet integrity service is unavailable" },
    { status: 503 },
  );

export async function POST(request: Request) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  let body: string;
  try {
    body = await request.text();
  } catch {
    return unavailableResponse();
  }

  let response: Response;
  try {
    response = await fetch(`${backendUrl}/api/v1/research-packet-integrity/verify`, {
      method: "POST",
      headers: { authorization: `Bearer ${token}`, "content-type": "application/json" },
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
    headers: { "content-type": "application/json" },
  });
}
