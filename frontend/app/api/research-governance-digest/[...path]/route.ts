import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
const unavailable = () =>
  NextResponse.json(
    { detail: "Research governance digest service is temporarily unavailable" },
    { status: 503 },
  );

async function forward(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const token = (await cookies()).get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  const { path } = await context.params;
  const encodedPath = path.map((segment) => encodeURIComponent(segment)).join("/");
  const incoming = new URL(request.url);
  const target = new URL(`${backendUrl}/api/v1/research-governance-digest/${encodedPath}`);
  target.search = incoming.search;

  let body: string | undefined;
  if (request.method !== "GET") {
    try {
      body = await request.text();
    } catch {
      return unavailable();
    }
  }

  let response: Response;
  try {
    response = await fetch(target, {
      method: request.method,
      headers: {
        authorization: `Bearer ${token}`,
        ...(body ? { "content-type": "application/json" } : {}),
      },
      body,
      cache: "no-store",
    });
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
    headers: { "content-type": "application/json" },
  });
}

export const GET = forward;
export const PUT = forward;
export const POST = forward;
