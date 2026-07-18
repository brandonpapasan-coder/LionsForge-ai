import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

function invalidRequestBody() {
  return NextResponse.json({ detail: "Invalid request body" }, { status: 400 });
}

function unavailable() {
  return NextResponse.json(
    { detail: "Authentication service is unavailable" },
    { status: 503 },
  );
}

export async function POST(request: Request) {
  let requestBody: string;
  try {
    requestBody = await request.text();
  } catch {
    return invalidRequestBody();
  }

  let response: Response;
  try {
    response = await fetch(`${backendUrl}/api/v1/auth/login`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: requestBody,
      cache: "no-store",
    });
  } catch {
    return unavailable();
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    return unavailable();
  }

  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }

  if (
    typeof payload !== "object" ||
    payload === null ||
    !("access_token" in payload) ||
    typeof payload.access_token !== "string"
  ) {
    return unavailable();
  }

  const result = NextResponse.json({ ok: true });
  result.cookies.set("lionsforge_session", payload.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 8,
  });
  return result;
}
