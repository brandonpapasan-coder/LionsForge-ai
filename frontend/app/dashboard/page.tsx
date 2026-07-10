import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { LogoutButton } from "@/components/logout-button";
import { ResearchReportForm } from "@/components/research-report-form";
import type { AuthUser } from "@/lib/auth";
import type { ResearchReportList } from "@/lib/research";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

async function getSessionData(): Promise<{ user: AuthUser; reports: ResearchReportList } | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) return null;

  const headers = { authorization: `Bearer ${token}` };
  const [userResponse, reportsResponse] = await Promise.all([
    fetch(`${backendUrl}/api/v1/auth/me`, { headers, cache: "no-store" }),
    fetch(`${backendUrl}/api/v1/research/reports`, { headers, cache: "no-store" }),
  ]);
  if (!userResponse.ok) return null;

  return {
    user: (await userResponse.json()) as AuthUser,
    reports: reportsResponse.ok
      ? ((await reportsResponse.json()) as ResearchReportList)
      : { symbol: null, reports: [] },
  };
}

export default async function DashboardPage() {
  const session = await getSessionData();
  if (!session) redirect("/login");

  return (
    <main>
      <header className="topbar dashboard-header">
        <div>
          <p className="eyebrow">LIONSFORGE AI WORKSPACE</p>
          <h1>Welcome, {session.user.full_name ?? session.user.email}.</h1>
        </div>
        <div className="session-actions">
          <div className="status online"><span aria-hidden="true" />Authenticated</div>
          <LogoutButton />
        </div>
      </header>

      <section className="workspace-links">
        <Link href="/education" className="workspace-link-card">
          <span>EDUCATION HUB</span>
          <strong>Continue your learning path</strong>
          <p>Explore finance, research methods, and advanced strategy modules.</p>
        </Link>
      </section>

      <section className="workspace-panel">
        <div>
          <p className="eyebrow">NEW RESEARCH</p>
          <h2>Generate and save an evidence-backed company report.</h2>
        </div>
        <ResearchReportForm />
      </section>

      <section className="saved-reports">
        <div className="section-heading">
          <div><p className="eyebrow">RESEARCH MEMORY</p><h2>Saved reports</h2></div>
          <span>{session.reports.reports.length} total</span>
        </div>
        <div className="report-grid">
          {session.reports.reports.length ? session.reports.reports.map((report) => (
            <Link className="report-card-link" href={`/reports/${report.report_id}`} key={report.report_id}>
              <article>
                <div className="report-meta"><span>{report.symbol}</span><span>{report.confidence_level} confidence</span></div>
                <h3>{report.title}</h3>
                <p>{report.executive_summary}</p>
                <small>{new Date(report.created_at).toLocaleString()}</small>
              </article>
            </Link>
          )) : <p className="empty-state">No saved reports yet. Generate your first report above.</p>}
        </div>
      </section>
    </main>
  );
}
