import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function PUT(
  request: Request,
  context: { params: Promise<{ lessonSlug: string }> },
) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });

  const { lessonSlug } = await context.params;

  try {
    const response = await fetch(
      `${backendUrl}/api/v1/education/lessons/${encodeURIComponent(lessonSlug)}/progress`,
      {
        method: "PUT",
        headers: {
          authorization: `Bearer ${token}`,
          "content-type": "application/json",
        },
        body: await request.text(),
        cache: "no-store",
      },
    );

    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return NextResponse.json(
      { detail: "Lesson progress service is unavailable" },
      { status: 503 },
    );
  }
}
