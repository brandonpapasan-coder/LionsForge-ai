import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

function unavailable() {
  return NextResponse.json(
    { detail: "Research sessions service is unavailable" },
    { status: 503 },
  );
}

function invalidRequestBody() {
  return NextResponse.json({ detail: "Invalid request body" }, { status: 400 });
}

async function proxy(
  request: Request,
  context: { params: Promise<{ projectId: string }> },
) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const { projectId } = await context.params;
  let body: string | undefined;

  if (request.method !== "GET") {
    try {
      body = await request.text();
    } catch {
      return invalidRequestBody();
    }
  }

  let response: Response;
  try {
    response = await fetch(
      `${backendUrl}/api/v1/research-projects/${encodeURIComponent(projectId)}/sessions`,
      {
        method: request.method,
        headers: {
          authorization: `Bearer ${token}`,
          "content-type": "application/json",
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
    headers: { "content-type": "application/json" },
  });
}

export async function GET(
  request: Request,
  context: { params: Promise<{ projectId: string }> },
) {
  return proxy(request, context);
}

export async function POST(
  request: Request,
  context: { params: Promise<{ projectId: string }> },
) {
  return proxy(request, context);
}
