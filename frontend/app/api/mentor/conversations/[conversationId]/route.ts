import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
const unavailableResponse = () =>
  NextResponse.json(
    { detail: "Mentor service is unavailable" },
    { status: 503 },
  );

export async function GET(
  _request: Request,
  context: { params: Promise<{ conversationId: string }> },
) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  try {
    const { conversationId } = await context.params;
    const response = await fetch(
      `${backendUrl}/api/v1/mentor/conversations/${encodeURIComponent(conversationId)}`,
      {
        headers: { authorization: `Bearer ${token}` },
        cache: "no-store",
      },
    );
    const body = await response.text();

    return new NextResponse(body, {
      status: response.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return unavailableResponse();
  }
}
