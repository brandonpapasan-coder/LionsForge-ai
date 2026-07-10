import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import type { AuthUser } from "@/lib/auth";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

async function getCurrentUser(): Promise<AuthUser | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) {
    return null;
  }

  const response = await fetch(`${backendUrl}/api/v1/auth/me`, {
    headers: { authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!response.ok) {
    return null;
  }
  return (await response.json()) as AuthUser;
}

export default async function DashboardPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }

  return (
    <main>
      <header className="topbar dashboard-header">
        <div>
          <p className="eyebrow">LIONSFORGE AI WORKSPACE</p>
          <h1>Welcome, {user.full_name ?? user.email}.</h1>
        </div>
        <div className="status online">
          <span aria-hidden="true" />
          Authenticated
        </div>
      </header>

      <section className="module-grid dashboard-grid" aria-label="Workspace modules">
        <article>
          <span>01</span>
          <h3>New research project</h3>
          <p>Begin an evidence-backed investigation and save it to your workspace.</p>
        </article>
        <article>
          <span>02</span>
          <h3>Validation center</h3>
          <p>Review sources, confidence, contradictions, and research assumptions.</p>
        </article>
        <article>
          <span>03</span>
          <h3>Education hub</h3>
          <p>Continue your personalized finance and research learning path.</p>
        </article>
        <article>
          <span>04</span>
          <h3>Saved reports</h3>
          <p>Reopen prior work and prepare professional report exports.</p>
        </article>
      </section>
    </main>
  );
}
