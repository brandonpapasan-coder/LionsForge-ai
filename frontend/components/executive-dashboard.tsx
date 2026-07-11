"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { ExecutiveDashboard as ExecutiveDashboardData } from "@/lib/dashboard";

export function ExecutiveDashboard() {
  const [data, setData] = useState<ExecutiveDashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const response = await fetch("/api/dashboard", { cache: "no-store" });
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) {
          setError("The executive dashboard could not be loaded.");
          return;
        }
        setData((await response.json()) as ExecutiveDashboardData);
      } catch {
        setError("The dashboard service is unavailable.");
      }
    }
    void load();
  }, []);

  if (error) {
    return <section className="dashboard-state" role="alert">{error}</section>;
  }
  if (!data) {
    return <section className="dashboard-state" aria-live="polite">Loading your command center…</section>;
  }

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
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <p>{metric.detail}</p>
          </article>
        ))}
      </section>

      <div className="dashboard-grid">
        <section className="dashboard-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">NEXT BEST ACTIONS</p>
              <h2>Focus your effort</h2>
            </div>
          </div>
          <div className="action-list">
            {data.next_actions.map((action) => (
              <Link href={action.href} className="action-card" key={`${action.title}-${action.href}`}>
                <div>
                  <span className={`priority priority-${action.priority}`}>{action.priority}</span>
                  <h3>{action.title}</h3>
                  <p>{action.reason}</p>
                </div>
                <span aria-hidden="true">→</span>
              </Link>
            ))}
          </div>
        </section>

        <section className="dashboard-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">RECENT ACTIVITY</p>
              <h2>Resume where you left off</h2>
            </div>
          </div>
          <div className="activity-list">
            {data.recent_activity.length ? data.recent_activity.map((activity) => (
              <Link href={activity.href} className="activity-card" key={`${activity.kind}-${activity.href}`}>
                <span>{activity.kind}</span>
                <div>
                  <strong>{activity.title}</strong>
                  <p>{activity.summary ?? "Continue this activity."}</p>
                </div>
              </Link>
            )) : <p className="muted">Your research and mentor activity will appear here.</p>}
          </div>
        </section>
      </div>
    </div>
  );
}
