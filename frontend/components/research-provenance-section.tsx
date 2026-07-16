"use client";

import { useEffect, useState } from "react";

import { ResearchProvenancePanel } from "@/components/research-provenance-panel";
import type { ResearchProject } from "@/lib/research";

const isAbortError = (error: unknown) => error instanceof DOMException && error.name === "AbortError";
const safeFilename = (title: string, projectId: number) => {
  const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 80) || `project-${projectId}`;
  return `${slug}-evidence-audit-packet.json`;
};

export function ResearchProvenanceSection() {
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch("/api/research-projects", { cache: "no-store", signal: controller.signal });
        if (controller.signal.aborted) return;
        if (response.status === 401) { window.location.href = "/login"; return; }
        if (!response.ok) { setError("Research projects could not be loaded for provenance review."); return; }
        const payload = (await response.json()) as ResearchProject[];
        setProjects(payload);
        setProjectId(payload[0]?.id ?? null);
      } catch (requestError) {
        if (!isAbortError(requestError) && !controller.signal.aborted) setError("The provenance project selector is unavailable.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  async function downloadAuditPacket() {
    if (!projectId) return;
    setDownloading(true);
    setError(null);
    try {
      const response = await fetch(`/api/research-evidence-audit-packet/${projectId}`, { cache: "no-store" });
      if (response.status === 401) { window.location.href = "/login"; return; }
      if (!response.ok) { setError("The evidence audit packet could not be generated."); return; }
      const packet = await response.json();
      const blob = new Blob([JSON.stringify(packet, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      const project = projects.find((item) => item.id === projectId);
      anchor.href = url;
      anchor.download = safeFilename(project?.title ?? `project-${projectId}`, projectId);
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("The evidence audit packet service is unavailable.");
    } finally {
      setDownloading(false);
    }
  }

  if (loading) return <section className="dashboard-state" aria-live="polite">Loading provenance projects…</section>;
  if (error && !projectId) return <section className="dashboard-state" role="alert">{error}</section>;
  if (!projectId) return null;

  return (
    <section className="research-provenance-section">
      <div className="research-section-heading">
        <div><p className="eyebrow">PROJECT EVIDENCE TRAIL</p><h2>Provenance ledger</h2></div>
        <div>
          <label>
            Research project
            <select aria-label="Provenance research project" value={projectId} onChange={(event) => setProjectId(Number(event.target.value))}>
              {projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}
            </select>
          </label>
          <button type="button" onClick={downloadAuditPacket} disabled={downloading}>
            {downloading ? "Preparing packet…" : "Download audit packet"}
          </button>
        </div>
      </div>
      {error ? <p role="alert" className="form-message">{error}</p> : null}
      <ResearchProvenancePanel projectId={projectId} />
    </section>
  );
}
