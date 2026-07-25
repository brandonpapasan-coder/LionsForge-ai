import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET() {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  try {
    const response = await fetch(`${backendUrl}/api/v1/investigations/review-queue/snapshot`, {
      headers: { authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    const headers = new Headers();
    for (const name of ["content-type", "content-disposition", "x-content-sha256"]) {
      const value = response.headers.get(name);
      if (value) headers.set(name, value);
    }
    return new NextResponse(await response.arrayBuffer(), {
      status: response.status,
      headers,
    });
  } catch {
    return NextResponse.json({ detail: "Review queue snapshot export is unavailable" }, { status: 503 });
  }
}
