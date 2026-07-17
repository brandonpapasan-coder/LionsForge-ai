import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
const unavailable = () =>
  NextResponse.json(
    { detail: "Evidence provenance ledger service is temporarily unavailable" },
    { status: 503 },
  );

export async function GET(request: Request) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const url = new URL(request.url);
  const projectId = url.searchParams.get("project_id");
  const suffix = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";

  let response: Response;
  try {
    response = await fetch(`${backendUrl}/api/v1/research-evidence-provenance/ledger${suffix}`, {
      headers: { authorization: `Bearer ${token}` },
      cache: "no-store",
    });
  } catch {
    return unavailable();
  }

  let body: string;
  try {
    body = await response.text();
  } catch {
    return unavailable();
  }

  return new NextResponse(body, {
    status: response.status,
    headers: { "content-type": "application/json" },
  });
}
