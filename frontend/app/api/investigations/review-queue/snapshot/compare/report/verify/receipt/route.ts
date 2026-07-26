import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  try {
    const response = await fetch(
      `${backendUrl}/api/v1/investigations/review-queue/snapshot/compare/report/verify/receipt`,
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
    const headers = new Headers();
    headers.set("content-type", response.headers.get("content-type") ?? "application/json");
    const disposition = response.headers.get("content-disposition");
    const digest = response.headers.get("x-content-sha256");
    if (disposition) headers.set("content-disposition", disposition);
    if (digest) headers.set("x-content-sha256", digest);
    return new NextResponse(await response.arrayBuffer(), { status: response.status, headers });
  } catch {
    return NextResponse.json(
      { detail: "Verification receipt export is unavailable" },
      { status: 503 },
    );
  }
}
