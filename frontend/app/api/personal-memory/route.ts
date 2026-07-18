import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
const supportedFilters = ["project_id", "status", "category", "query"] as const;

function unavailable() {
  return NextResponse.json(
    { detail: "Personal memory service is unavailable" },
    { status: 503 },
  );
}

export async function GET(request: Request) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const incomingUrl = new URL(request.url);
  const target = new URL(`${backendUrl}/api/v1/knowledge-memory`);
  for (const filter of supportedFilters) {
    const value = incomingUrl.searchParams.get(filter);
    if (value) target.searchParams.set(filter, value);
  }

  try {
    const response = await fetch(target, {
      method: "GET",
      headers: { authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return unavailable();
  }
}
