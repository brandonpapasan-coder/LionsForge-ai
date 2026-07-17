import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
const unavailableResponse = () =>
  NextResponse.json({ detail: "Research conclusion defense export service unavailable" }, { status: 503 });

export async function GET(
  _request: Request,
  context: { params: Promise<{ projectId: string }> },
) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  const { projectId } = await context.params;

  let response: Response;
  try {
    response = await fetch(
      `${backendUrl}/api/v1/research-conclusion-defense-export/projects/${encodeURIComponent(projectId)}`,
      { headers: { authorization: `Bearer ${token}` }, cache: "no-store" },
    );
  } catch {
    return unavailableResponse();
  }

  let body: string;
  try {
    body = await response.text();
  } catch {
    return unavailableResponse();
  }

  return new NextResponse(body, {
    status: response.status,
    headers: { "content-type": "application/json" },
  });
}
