import { cookies } from "next/headers";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import type { ResearchReportDetail } from "@/lib/research";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

async function getReport(reportId: string): Promise<ResearchReportDetail | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) {
    redirect("/login");
  }

  const response = await fetch(`${backendUrl}/api/v1/research/reports/${encodeURIComponent(reportId)}`, {
    headers: { authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    redirect("/dashboard");
  }
  return (await response.json()) as ResearchReportDetail;
}

export default async function ReportPage({ params }: { params: Promise<{ reportId: string }> }) {
  const { reportId } = await params;
  const report = await getReport(reportId);
  if (!report) {
    notFound();
  }

  const sections = report.report_payload.sections ?? [];

  return (
    <main>
      <div className="report-toolbar">
        <Link href="/dashboard" className="back-link">← Back to dashboard</Link>
        <a className="export-link" href={`/api/research/reports/${report.report_id}/export`}>
          Download Markdown
        </a>
      </div>
      <header className="report-header">
        <div>
          <p className="eyebrow">{report.symbol} · SAVED RESEARCH</p>
          <h1>{report.title}</h1>
          <p className="lede">{report.executive_summary}</p>
        </div>
        <aside className="report-facts">
          <div><span>Status</span><strong>{report.status}</strong></div>
          <div><span>Confidence</span><strong>{report.confidence_level}</strong></div>
          <div><span>Score</span><strong>{report.confidence_score}</strong></div>
          <div><span>Version</span><strong>{report.version}</strong></div>
        </aside>
      </header>

      <section className="report-sections">
        {sections.map((section) => (
          <article key={section.title}>
            <h2>{section.title}</h2>
            <p>{section.summary}</p>
            {section.bullets?.length ? (
              <ul>{section.bullets.map((bullet) => <li key={bullet}>{bullet}</li>)}</ul>
            ) : null}
          </article>
        ))}
      </section>
    </main>
  );
}
