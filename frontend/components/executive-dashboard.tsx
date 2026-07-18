"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { KnowledgeQualityDashboard } from "@/components/knowledge-quality-dashboard";
import { MarketLearningEvidencePanel } from "@/components/market-learning-evidence-panel";
import { MarketLearningMasteryPanel } from "@/components/market-learning-mastery-panel";
import { MarketLearningPortfolioPanel } from "@/components/market-learning-portfolio-panel";
import { MarketLearningProgressPanel } from "@/components/market-learning-progress-panel";
import { MarketLearningRoadmapPanel } from "@/components/market-learning-roadmap-panel";
import { PersonalMemoryControlCenter } from "@/components/personal-memory-control-center";
import { PersonalMemoryEvidenceHealthInventory } from "@/components/personal-memory-evidence-health-inventory";
import { PersonalMemoryEvidenceRemediation } from "@/components/personal-memory-evidence-remediation";
import { PersonalMemoryEvidenceRemediationEscalations } from "@/components/personal-memory-evidence-remediation-escalations";
import { PersonalMemoryEvidenceRemediationVerification } from "@/components/personal-memory-evidence-remediation-verification";
import type { ExecutiveDashboard as ExecutiveDashboardData } from "@/lib/dashboard";

export function ExecutiveDashboard() {
  const [data, setData] = useState<ExecutiveDashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    const controller = new AbortController();

    async function load() {
      try {
        const response = await fetch("/api/dashboard", {
          cache: "no-store",
          signal: controller.signal,
        });
        if (controller.signal.aborted || !mounted.current) return;
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) {
          setError("The executive dashboard could not be loaded.");
          return;
        }
        const payload = (await response.json()) as ExecutiveDashboardData;
        if (!controller.signal.aborted && mounted.current) setData(payload);
      } catch (requestError) {
        if (requestError instanceof DOMException && requestError.name === "AbortError") return;
        if (!controller.signal.aborted && mounted.current) setError("The dashboard service is unavailable.");
      }
    }

    void load();
    return () => {
      mounted.current = false;
      controller.abort();
    };
  }, []);

  if (error) return <section className="dashboard-state" role="alert">{error}</section>;
  if (!data) return <section className="dashboard-state" aria-live="polite">Loading your command center…</section>;

  return (
    <div className="dashboard-shell">
      <header className="dashboard-hero">
        <div>
          <p className="eyebrow">EXECUTIVE COMMAND CENTER</p>
          <h1>{data.greeting}</h1>
          <p>{data.briefing}</p>
        </div>
        <Link className="primary-link" href="/mentor">Open AI Mentor</Link>
      </header>

      <section className="metric-grid" aria-label="Platform metrics">
        {data.metrics.map((metric) => (
          <article className="metric-card" key={metric.label}>
            <span>{metric.label}</span><strong>{metric.value}</strong><p>{metric.detail}</p>
          </article>
        ))}
      </section>

      <PersonalMemoryEvidenceHealthInventory />
      <PersonalMemoryControlCenter />
      <PersonalMemoryEvidenceRemediation />
      <PersonalMemoryEvidenceRemediationVerification />
      <PersonalMemoryEvidenceRemediationEscalations />
      <KnowledgeQualityDashboard />
      <MarketLearningProgressPanel />
      <MarketLearningRoadmapPanel />
      <MarketLearningMasteryPanel />
      <MarketLearningEvidencePanel />
      <MarketLearningPortfolioPanel />

      <div className="dashboard-grid">
        <section className="dashboard-panel">
          <div className="panel-heading"><div><p className="eyebrow">NEXT BEST ACTIONS</p><h2>Focus your effort</h2></div></div>
          <div className="action-list">
            {data.next_actions.map((action) => (
              <Link href={action.href} className="action-card" key={`${action.title}-${action.href}`}>
                <div><span className={`priority priority-${action.priority}`}>{action.priority}</span><h3>{action.title}</h3><p>{action.reason}</p></div><span aria-hidden="true">→</span>
              </Link>
            ))}
          </div>
        </section>

        <section className="dashboard-panel">
          <div className="panel-heading"><div><p className="eyebrow">RECENT ACTIVITY</p><h2>Resume where you left off</h2></div></div>
          <div className="activity-list">
            {data.recent_activity.length ? data.recent_activity.map((activity) => (
              <Link href={activity.href} className="activity-card" key={`${activity.kind}-${activity.href}`}>
                <span>{activity.kind}</span><div><strong>{activity.title}</strong><p>{activity.summary ?? "Continue this activity."}</p></div>
              </Link>
            )) : <p className="muted">Your research and mentor activity will appear here.</p>}
          </div>
        </section>
      </div>
    </div>
  );
}
