import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(
  request: Request,
  context: { params: Promise<{ courseId: string; moduleId: string }> },
) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const { courseId, moduleId } = await context.params;
  const response = await fetch(
    `${backendUrl}/api/v1/education/courses/${encodeURIComponent(courseId)}/modules/${encodeURIComponent(moduleId)}/assessment`,
    {
      method: "POST",
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
}
