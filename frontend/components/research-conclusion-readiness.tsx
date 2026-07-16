"use client";

import { useEffect, useState } from "react";

import type { ResearchProject } from "@/lib/research";

type ReadinessState = "blocked" | "needs_review" | "ready_for_user_conclusion";
type ReadinessCheck = {
  code: string;
  level: "blocking" | "caution" | "informational";
  passed: boolean;
  message: string;
  evidence_ids: number[];
  action_ids: number[];
  event_ids: string[];
  governing_rules: string[];
};
type Readiness = {
  project_id: number;
  state: ReadinessState;
  evidence_count: number;
  blocking_count: number;
  caution_count: number;
  checks: ReadinessCheck[];
  next_steps: string[];
  disclaimer: string;
};

const stateLabels: Record<ReadinessState, string> = {
  blocked: "Blocked",
  needs_review: "Needs review",
  ready_for_user_conclusion: "Ready for user conclusion",
};

export function ResearchConclusionReadiness() {
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetch("/api/research-projects", { cache: "no-store" })
      .then(async (response) => {
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) throw new Error();
        const body = (await response.json()) as ResearchProject[];
        setProjects(body);
        setProjectId(body[0]?.id ?? null);
      })
      .catch(() => setError("Research projects could not be loaded."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!projectId) return;
    setError(null);
    void fetch(`/api/research-conclusion-readiness/projects/${projectId}`, { cache: "no-store" })
      .then(async (response) => {
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) throw new Error();
        setReadiness((await response.json()) as Readiness);
      })
      .catch(() => setError("Conclusion readiness could not be loaded."));
  }, [projectId]);

  if (loading) return <section className="dashboard-state">Loading conclusion readiness…</section>;
  if (!projectId) return <section className="dashboard-state">Create a research project to evaluate conclusion readiness.</section>;

  return (
    <section className="research-provenance-section">
      <div className="research-section-heading">
        <div>
          <p className="eyebrow">RESEARCH WORKSPACE</p>
          <h1>Conclusion readiness</h1>
          <p className="muted">Review workflow completeness and provenance risk before drafting your own conclusion.</p>
        </div>
      </div>

      {error ? <p role="alert" className="form-message">{error}</p> : null}

      <section className="dashboard-panel">
        <label>
          Project
          <select aria-label="Readiness project" value={projectId} onChange={(event) => setProjectId(Number(event.target.value))}>
            {projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}
          </select>
        </label>
      </section>

      {readiness ? <>
        <div className="metric-grid">
          <article><strong>{stateLabels[readiness.state]}</strong><span>Readiness</span></article>
          <article><strong>{readiness.evidence_count}</strong><span>Evidence records</span></article>
          <article><strong>{readiness.blocking_count}</strong><span>Blocking checks</span></article>
          <article><strong>{readiness.caution_count}</strong><span>Cautions</span></article>
        </div>

        <section className="dashboard-panel">
          <div className="panel-heading"><div><p className="eyebrow">DETERMINISTIC GATE</p><h2>Readiness checks</h2><p className="muted">{readiness.disclaimer}</p></div></div>
          <div className="activity-list">
            {readiness.checks.map((check) => <article className="activity-card" key={check.code}>
              <span>{check.passed ? "PASSED" : check.level.toUpperCase()}</span>
              <div>
                <strong>{check.code.replaceAll("_", " ")}</strong>
                <p>{check.message}</p>
                {(check.evidence_ids.length || check.action_ids.length || check.event_ids.length || check.governing_rules.length) ? <details>
                  <summary>Traceability</summary>
                  {check.evidence_ids.length ? <p><strong>Evidence:</strong> {check.evidence_ids.join(", ")}</p> : null}
                  {check.action_ids.length ? <p><strong>Actions:</strong> {check.action_ids.join(", ")}</p> : null}
                  {check.event_ids.length ? <p><strong>Events:</strong> {check.event_ids.join(", ")}</p> : null}
                  {check.governing_rules.length ? <p><strong>Rules:</strong> {check.governing_rules.join(", ")}</p> : null}
                </details> : null}
              </div>
            </article>)}
          </div>
        </section>

        <section className="dashboard-panel">
          <div className="panel-heading"><div><p className="eyebrow">USER-CONTROLLED NEXT STEPS</p><h2>What remains</h2></div></div>
          <ul>{readiness.next_steps.map((step) => <li key={step}>{step}</li>)}</ul>
        </section>
      </> : null}
    </section>
  );
}
