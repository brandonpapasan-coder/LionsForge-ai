import { NextResponse } from "next/server";

import type { AuthCredentials, AuthToken } from "@/lib/auth";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const payload = (await request.json()) as AuthCredentials;
  const response = await fetch(`${backendUrl}/api/v1/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = (await response.json().catch(() => null)) as { detail?: string } | null;
    return NextResponse.json(
      { ok: false, message: detail?.detail ?? "Unable to sign in." },
      { status: response.status },
    );
  }

  const token = (await response.json()) as AuthToken;
  const result = NextResponse.json({ ok: true, message: "Signed in successfully." });
  result.cookies.set("lionsforge_session", token.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60,
  });
  return result;
}
