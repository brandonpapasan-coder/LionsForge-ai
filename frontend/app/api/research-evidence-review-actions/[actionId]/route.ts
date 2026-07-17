import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
const unavailableDetail = "Review action service is temporarily unavailable";

export async function PATCH(request: Request, context: { params: Promise<{ actionId: string }> }) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON payload" }, { status: 400 });
  }

  const { actionId } = await context.params;
  let response: Response;
  try {
    response = await fetch(
      `${backendUrl}/api/v1/research-evidence-audit/review-actions/${encodeURIComponent(actionId)}`,
      {
        method: "PATCH",
        headers: { authorization: `Bearer ${token}`, "content-type": "application/json" },
        body: JSON.stringify(payload),
        cache: "no-store",
      },
    );
  } catch {
    return NextResponse.json({ detail: unavailableDetail }, { status: 503 });
  }

  let body: string;
  try {
    body = await response.text();
  } catch {
    return NextResponse.json({ detail: unavailableDetail }, { status: 503 });
  }

  return new NextResponse(body, {
    status: response.status,
    headers: { "content-type": "application/json" },
  });
}
