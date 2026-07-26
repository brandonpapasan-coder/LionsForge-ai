import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  try {
    const response = await fetch(
      `${backendUrl}/api/v1/investigations/review-queue/snapshot/compare/report/verify`,
      {
        method: "POST",
        headers: {
          authorization: `Bearer ${token}`,
          "content-type": "application/json",
        },
        body: await request.text(),
        cache: "no-store",
      },
    );
    return new NextResponse(await response.arrayBuffer(), {
      status: response.status,
      headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json(
      { detail: "Comparison report verification is unavailable" },
      { status: 503 },
    );
  }
}
