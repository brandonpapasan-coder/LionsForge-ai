import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";
const unavailable = () =>
  NextResponse.json(
    { detail: "Comparison report integrity service is temporarily unavailable" },
    { status: 503 },
  );

export async function POST(request: Request) {
  const session = (await cookies()).get("lionsforge_session")?.value;
  if (!session) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  let body: string;
  try {
    body = await request.text();
  } catch {
    return unavailable();
  }

  let response: Response;
  try {
    response = await fetch(
      `${BACKEND_URL}/api/v1/research-packet-comparison-report-integrity/verify`,
      {
        method: "POST",
        headers: {
          "content-type": "application/json",
          authorization: `Bearer ${session}`,
        },
        body,
        cache: "no-store",
      },
    );
  } catch {
    return unavailable();
  }

  let responseBody: string;
  try {
    responseBody = await response.text();
  } catch {
    return unavailable();
  }

  return new NextResponse(responseBody, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
}
