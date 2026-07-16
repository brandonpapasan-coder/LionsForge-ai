"use client";

import { useEffect, useState } from "react";

import { ResearchProvenancePanel } from "@/components/research-provenance-panel";
import type { ResearchProject } from "@/lib/research";

const isAbortError = (error: unknown) => error instanceof DOMException && error.name === "AbortError";

export function ResearchProvenanceSection() {
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        const response = await fetch("/api/research-projects", { cache: "no-store", signal: controller.signal });
        if (controller.signal.aborted) return;
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) {
          setError("Research projects could not be loaded for provenance review.");
          return;
        }
        const payload = (await response.json()) as ResearchProject[];
        setProjects(payload);
        setProjectId(payload[0]?.id ?? null);
      } catch (requestError) {
        if (!isAbortError(requestError) && !controller.signal.aborted) {
          setError("The provenance project selector is unavailable.");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void load();
    return () => controller.abort();
  }, []);

  if (loading) return <section className="dashboard-state" aria-live="polite">Loading provenance projects…</section>;
  if (error) return <section className="dashboard-state" role="alert">{error}</section>;
  if (!projectId) return null;

  return (
    <section className="research-provenance-section">
      <div className="research-section-heading">
        <div><p className="eyebrow">PROJECT EVIDENCE TRAIL</p><h2>Provenance ledger</h2></div>
        <label>
          Research project
          <select aria-label="Provenance research project" value={projectId} onChange={(event) => setProjectId(Number(event.target.value))}>
            {projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}
          </select>
        </label>
      </div>
      <ResearchProvenancePanel projectId={projectId} />
    </section>
  );
}
