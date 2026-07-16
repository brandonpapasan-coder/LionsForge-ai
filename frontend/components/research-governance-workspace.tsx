"use client";

import { useEffect, useState } from "react";

import { ResearchGovernanceDashboard } from "@/components/research-governance-dashboard";
import type { ResearchProject } from "@/lib/research";

export function ResearchGovernanceWorkspace() {
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch("/api/research-projects", { cache: "no-store", signal: controller.signal });
        if (response.status === 401) { window.location.href = "/login"; return; }
        if (!response.ok) { setError("Research projects could not be loaded."); return; }
        const payload = (await response.json()) as ResearchProject[];
        setProjects(payload);
        setProjectId(payload[0]?.id ?? null);
      } catch (requestError) {
        if (!(requestError instanceof DOMException && requestError.name === "AbortError")) setError("The governance workspace is unavailable.");
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  return <section className="research-provenance-section">
    <div className="research-section-heading"><div><p className="eyebrow">RESEARCH WORKSPACE</p><h2>Governance review dashboard</h2></div>{projects.length ? <label>Research project<select aria-label="Governance research project" value={projectId ?? ""} onChange={(event) => setProjectId(Number(event.target.value))}>{projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}</select></label> : null}</div>
    {error ? <p role="alert" className="form-message">{error}</p> : null}
    {projectId ? <ResearchGovernanceDashboard projectId={projectId} /> : <section className="dashboard-state">No research project is available for governance review.</section>}
  </section>;
}
