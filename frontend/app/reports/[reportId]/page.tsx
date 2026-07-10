import { cookies } from "next/headers";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import type { ResearchReportDetail } from "@/lib/research";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

async function getReport(reportId: string): Promise<ResearchReportDetail | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) redirect("/login");
  const response = await fetch(`${backendUrl}/api/v1/research/reports/${encodeURIComponent(reportId)}`, {
    headers: { authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (response.status === 404) return null;
  if (!response.ok) redirect("/dashboard");
  return (await response.json()) as ResearchReportDetail;
}

function InsightList({ title, items }: { title: string; items?: string[] }) {
  if (!items?.length) return null;
  return <article><h2>{title}</h2><ul>{items.map((item) => <li key={item}>{item}</li>)}</ul></article>;
}

export default async function ReportPage({ params }: { params: Promise<{ reportId: string }> }) {
  const { reportId } = await params;
  const report = await getReport(reportId);
  if (!report) notFound();
  const sections = report.report_payload.sections ?? [];

  return (
    <main>
      <div className="report-toolbar">
        <Link href="/dashboard" className="back-link">← Back to dashboard</Link>
        <a className="export-link" href={`/api/research/reports/${report.report_id}/export`}>Download Markdown</a>
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
          <div><span>Evidence</span><strong>{report.evidence_payload.length}</strong></div>
        </aside>
      </header>

      <section className="report-sections">
        {sections.map((section) => <article key={section.title}><h2>{section.title}</h2><p>{section.summary}</p>{section.bullets?.length ? <ul>{section.bullets.map((bullet) => <li key={bullet}>{bullet}</li>)}</ul> : null}</article>)}
        <InsightList title="Bull Case" items={report.report_payload.bull_case} />
        <InsightList title="Bear Case" items={report.report_payload.bear_case} />
        <InsightList title="Risks" items={report.report_payload.risks} />
        <InsightList title="Opportunities" items={report.report_payload.opportunities} />
        <InsightList title="Assumptions" items={report.report_payload.assumptions} />
      </section>

      <section className="evidence-section">
        <p className="eyebrow">VALIDATION EVIDENCE</p>
        <h2>Persisted evidence</h2>
        <div className="evidence-grid">
          {report.evidence_payload.map((item) => (
            <article key={item.evidence_id}>
              <div className="report-meta"><span>{item.category}</span><span>{item.confidence}</span></div>
              <h3>{item.title}</h3>
              <p>{item.summary ?? "No evidence summary available."}</p>
              <small>{item.source} · {new Date(item.observed_at).toLocaleString()}</small>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
