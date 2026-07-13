"use client";

import { useEffect, useState } from "react";

import type { KnowledgeQualityDashboard as KnowledgeQualityDashboardData } from "@/lib/knowledge-quality";
import type { ResearchProject } from "@/lib/research";

const percent = (value: number) => `${Math.round(value * 100)}%`;
const label = (value: string) => value.replaceAll("_", " ");

export function KnowledgeQualityDashboard() {
  const [data, setData] = useState<KnowledgeQualityDashboardData | null>(null);
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("organization");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadDashboard(projectId: string) {
    setLoading(true);
    setError(null);
    try {
      const path = projectId === "organization"
        ? "/api/knowledge-quality"
        : `/api/knowledge-quality/projects/${projectId}`;
      const response = await fetch(path, { cache: "no-store" });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (response.status === 404) {
        setData(null);
        setError("That research project could not be found or is not available to this account.");
        return;
      }
      if (!response.ok) {
        setError("Institutional knowledge quality could not be loaded.");
        return;
      }
      setData((await response.json()) as KnowledgeQualityDashboardData);
    } catch {
      setError("The knowledge quality service is unavailable.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    async function initialize() {
      try {
        const response = await fetch("/api/research-projects", { cache: "no-store" });
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (response.ok) {
          setProjects((await response.json()) as ResearchProject[]);
        }
      } finally {
        await loadDashboard("organization");
      }
    }
    void initialize();
  }, []);

  async function changeScope(projectId: string) {
    setSelectedProjectId(projectId);
    await loadDashboard(projectId);
  }

  if (loading && !data) {
    return <section className="dashboard-state" aria-live="polite">Loading institutional knowledge health…</section>;
  }

  if (error && !data) {
    return (
      <section className="dashboard-panel" aria-labelledby="knowledge-quality-title">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">INSTITUTIONAL KNOWLEDGE QUALITY</p>
            <h2 id="knowledge-quality-title">Research health and review burden</h2>
          </div>
        </div>
        <label>
          Knowledge scope
          <select value={selectedProjectId} onChange={(event) => void changeScope(event.target.value)}>
            <option value="organization">All owned projects</option>
            {projects.map((project) => <option key={project.id} value={String(project.id)}>{project.title}</option>)}
          </select>
        </label>
        <p role="alert">{error}</p>
      </section>
    );
  }

  if (!data) return null;

  const hasKnowledge = data.memories.total > 0 || data.evidence_total > 0;
  const selectedProject = projects.find((project) => String(project.id) === selectedProjectId);
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
          <p className="muted">
            {selectedProject ? `Project: ${selectedProject.title} · ` : "Organization-wide · "}
            Methodology {data.methodology_version} · Generated {new Date(data.generated_at).toLocaleString()}
          </p>
        </div>
        <label>
          Knowledge scope
          <select value={selectedProjectId} onChange={(event) => void changeScope(event.target.value)} disabled={loading}>
            <option value="organization">All owned projects</option>
            {projects.map((project) => <option key={project.id} value={String(project.id)}>{project.title}</option>)}
          </select>
        </label>
      </div>

      {error && <p role="alert">{error}</p>}
      {loading && <p className="muted" aria-live="polite">Refreshing knowledge health…</p>}
      {!hasKnowledge && <p className="muted">No research baseline exists for this scope yet. Scores remain unset until evidence or knowledge records are available.</p>}

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
