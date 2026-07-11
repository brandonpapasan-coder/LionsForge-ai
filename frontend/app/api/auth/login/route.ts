import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const response = await fetch(`${backendUrl}/api/v1/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: await request.text(),
    cache: "no-store",
  });
  const payload = await response.json();
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
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
