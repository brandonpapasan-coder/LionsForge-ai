import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET() {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  let response: Response;
  try {
    response = await fetch(`${backendUrl}/api/v1/education/assessment/trends`, {
      headers: { authorization: `Bearer ${token}` },
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { detail: "Education competency trend service is unavailable" },
      { status: 503 },
    );
  }

  let responseBody: string;
  try {
    responseBody = await response.text();
  } catch {
    return NextResponse.json(
      { detail: "Education competency trend service is unavailable" },
      { status: 503 },
    );
  }

  return new NextResponse(responseBody, {
    status: response.status,
    headers: { "content-type": "application/json" },
  });
}
