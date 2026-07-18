import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

function unavailable() {
  return NextResponse.json(
    { detail: "Lesson progress service is unavailable" },
    { status: 503 },
  );
}

function invalidRequestBody() {
  return NextResponse.json({ detail: "Invalid request body" }, { status: 400 });
}

export async function PUT(
  request: Request,
  context: { params: Promise<{ lessonSlug: string }> },
) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  const { lessonSlug } = await context.params;

  let body: string;
  try {
    body = await request.text();
  } catch {
    return invalidRequestBody();
  }

  let response: Response;
  try {
    response = await fetch(
      `${backendUrl}/api/v1/education/lessons/${encodeURIComponent(lessonSlug)}/progress`,
      {
        method: "PUT",
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
