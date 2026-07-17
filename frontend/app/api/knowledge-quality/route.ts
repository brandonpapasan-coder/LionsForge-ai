import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET() {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  try {
    const response = await fetch(`${backendUrl}/api/v1/knowledge-quality/dashboard`, {
      headers: { authorization: `Bearer ${token}` },
      cache: "no-store",
    });

    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return NextResponse.json(
      { detail: "Knowledge quality service is unavailable" },
      { status: 503 },
    );
  }
}
