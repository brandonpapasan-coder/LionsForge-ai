import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import type { ResearchReportDetail } from "@/lib/research";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

function toMarkdown(report: ResearchReportDetail): string {
  const sections = report.report_payload.sections ?? [];
  const lines = [
    `# ${report.title}`,
    "",
    `**Symbol:** ${report.symbol}`,
    `**Status:** ${report.status}`,
    `**Confidence:** ${report.confidence_level} (${report.confidence_score})`,
    `**Version:** ${report.version}`,
    `**Created:** ${report.created_at}`,
    "",
    "## Executive Summary",
    "",
    report.executive_summary,
    "",
  ];

  for (const section of sections) {
    lines.push(`## ${section.title}`, "", section.summary, "");
    for (const bullet of section.bullets ?? []) {
      lines.push(`- ${bullet}`);
    }
    lines.push("");
  }

  const appendList = (title: string, items?: string[]) => {
    if (!items?.length) return;
    lines.push(`## ${title}`, "", ...items.map((item) => `- ${item}`), "");
  };

  appendList("Bull Case", report.report_payload.bull_case);
  appendList("Bear Case", report.report_payload.bear_case);
  appendList("Risks", report.report_payload.risks);
  appendList("Opportunities", report.report_payload.opportunities);
  appendList("Assumptions", report.report_payload.assumptions);

  return lines.join("\n");
}

export async function GET(
  _request: Request,
  context: { params: Promise<{ reportId: string }> },
) {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const { reportId } = await context.params;
  const response = await fetch(`${backendUrl}/api/v1/research/reports/${encodeURIComponent(reportId)}`, {
    headers: { authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!response.ok) {
    return NextResponse.json({ detail: "Report not found" }, { status: response.status });
  }

  const report = (await response.json()) as ResearchReportDetail;
  const filename = `${report.symbol.toLowerCase()}-${report.report_id}.md`;
  return new NextResponse(toMarkdown(report), {
    status: 200,
    headers: {
      "content-type": "text/markdown; charset=utf-8",
      "content-disposition": `attachment; filename="${filename}"`,
      "cache-control": "no-store",
    },
  });
}
