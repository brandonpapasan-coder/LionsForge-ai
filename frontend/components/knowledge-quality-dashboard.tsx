"use client";

import { useEffect, useState } from "react";

import type { KnowledgeQualityDashboard as KnowledgeQualityDashboardData } from "@/lib/knowledge-quality";

const percent = (value: number) => `${Math.round(value * 100)}%`;
const label = (value: string) => value.replaceAll("_", " ");

export function KnowledgeQualityDashboard() {
  const [data, setData] = useState<KnowledgeQualityDashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const response = await fetch("/api/knowledge-quality", { cache: "no-store" });
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) {
          setError("Institutional knowledge quality could not be loaded.");
          return;
        }
        setData((await response.json()) as KnowledgeQualityDashboardData);
      } catch {
        setError("The knowledge quality service is unavailable.");
      }
    }
    void load();
  }, []);

  if (error) return <section className="dashboard-state" role="alert">{error}</section>;
  if (!data) return <section className="dashboard-state" aria-live="polite">Loading institutional knowledge health…</section>;

  const hasKnowledge = data.memories.total > 0 || data.evidence_total > 0;
  const metrics = [
    ["Health score", hasKnowledge ? percent(data.health_score) : "No baseline", "Composite advisory indicator; it does not validate research."],
    ["Validated knowledge", String(data.memories.validated), `${data.memories.provisional} provisional and ${data.memories.contested} contested records`],
    ["Evidence coverage", percent(data.evidence_coverage_ratio), `${data.evidence_approved} approved of ${data.evidence_total} evidence records`],
    ["Review backlog", String(data.review_backlog), `${data.evidence_pending_review} evidence records pending review`],
    ["Average confidence", percent(data.average_confidence), `Median confidence ${percent(data.median_confidence)}`],
    ["Open contradictions", String(data.unresolved_contradictions), `Contradiction rate ${percent(data.contradiction_rate)}`],
  ];

  return (
    <section className="dashboard-panel" aria-labelledby="knowledge-quality-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">INSTITUTIONAL KNOWLEDGE QUALITY</p>
          <h2 id="knowledge-quality-title">Research health and review burden</h2>
          <p className="muted">Methodology {data.methodology_version} · Generated {new Date(data.generated_at).toLocaleString()}</p>
        </div>
      </div>

      {!hasKnowledge && <p className="muted">No research baseline exists yet. Scores remain unset until evidence or knowledge records are available.</p>}

      <div className="metric-grid" aria-label="Knowledge quality metrics">
        {metrics.map(([name, value, detail]) => (
          <article className="metric-card" key={name}>
            <span>{name}</span>
            <strong>{value}</strong>
            <p>{detail}</p>
          </article>
        ))}
      </div>

      <div className="dashboard-grid">
        <section>
          <div className="panel-heading"><div><p className="eyebrow">HEALTH COMPONENTS</p><h3>How the score is formed</h3></div></div>
          <div className="activity-list">
            {Object.entries(data.health_components).map(([name, value]) => (
              <div className="activity-card" key={name}>
                <span>{percent(value)}</span>
                <div><strong>{label(name)}</strong><p>Transparent component contribution to the advisory health score.</p></div>
              </div>
            ))}
          </div>
        </section>

        <section>
          <div className="panel-heading"><div><p className="eyebrow">TOP RISKS</p><h3>Items requiring attention</h3></div></div>
          <div className="activity-list">
            {data.top_risks.length ? data.top_risks.map((risk) => (
              <div className="activity-card" key={`${risk.risk_type}-${risk.title}`}>
                <span>{percent(risk.severity)}</span>
                <div><strong>{risk.title}</strong><p>{risk.detail}</p></div>
              </div>
            )) : <p className="muted">No ranked knowledge risks are currently reported.</p>}
          </div>
        </section>
      </div>

      <div className="panel-heading"><div><p className="eyebrow">RECENT KNOWLEDGE ACTIVITY</p><h3>Latest reviewed changes</h3></div></div>
      <div className="activity-list">
        {data.recent_activity.length ? data.recent_activity.slice(0, 8).map((activity) => (
          <div className="activity-card" key={`${activity.record_type}-${activity.record_id}`}>
            <span>{label(activity.status)}</span>
            <div><strong>{activity.title}</strong><p>{label(activity.record_type)} · {new Date(activity.occurred_at).toLocaleString()}</p></div>
          </div>
        )) : <p className="muted">Knowledge revisions and review activity will appear here.</p>}
      </div>
    </section>
  );
}
