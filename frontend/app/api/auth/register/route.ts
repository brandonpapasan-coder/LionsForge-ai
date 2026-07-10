import { NextResponse } from "next/server";

import type { AuthCredentials, AuthUser } from "@/lib/auth";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const payload = (await request.json()) as AuthCredentials;
  const response = await fetch(`${backendUrl}/api/v1/auth/register`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = (await response.json().catch(() => null)) as { detail?: string } | null;
    return NextResponse.json(
      { ok: false, message: detail?.detail ?? "Unable to create account." },
      { status: response.status },
    );
  }

  const user = (await response.json()) as AuthUser;
  return NextResponse.json(
    { ok: true, message: "Account created. You can now sign in.", user },
    { status: 201 },
  );
}
