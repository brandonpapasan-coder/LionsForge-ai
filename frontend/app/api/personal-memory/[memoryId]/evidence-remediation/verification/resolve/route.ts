import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
type Context = { params: Promise<{ memoryId: string }> };

function unavailable() {
  return NextResponse.json(
    { detail: "Personal memory remediation resolution service is unavailable" },
    { status: 503 },
  );
}

export async function POST(request: Request, context: Context) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  const { memoryId } = await context.params;
  try {
    const response = await fetch(
      `${backendUrl}/api/v1/knowledge-memory/${encodeURIComponent(memoryId)}/evidence-remediation/verification/resolve`,
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
  } catch {
    return unavailable();
  }
}
