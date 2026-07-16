"use client";

import { useEffect, useState } from "react";
import type { ResearchProject } from "@/lib/research";

type Evidence = { id: number; source_title: string; claim: string; validation_status: string };
type Revision = { revision_number: number; status: string; revision_note: string | null; created_at: string };
type Packet = {
  content_sha256: string;
  generated_at: string;
  content: {
    schema_version: string;
    project_id: number;
    project_title: string;
    conclusion_status: string;
    conclusion_text: string;
    evidence_ids: number[];
    evidence: Evidence[];
    revisions: Revision[];
    readiness: { state: string; blocking_count: number; caution_count: number; next_steps: string[]; disclaimer: string };
    disclaimer: string;
  };
};

export function ResearchConclusionExportPacket() {
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [packet, setPacket] = useState<Packet | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetch("/api/research-projects", { cache: "no-store" }).then(async (response) => {
      if (response.status === 401) { window.location.href = "/login"; return; }
      if (!response.ok) throw new Error();
      const body = await response.json() as ResearchProject[];
      setProjects(body); setProjectId(body[0]?.id ?? null);
    }).catch(() => setError("Research projects could not be loaded."));
  }, []);

  useEffect(() => {
    if (!projectId) return;
    void fetch(`/api/research-conclusion-export/${projectId}`, { cache: "no-store" }).then(async (response) => {
      if (response.status === 401) { window.location.href = "/login"; return; }
      if (!response.ok) throw new Error();
      setPacket(await response.json() as Packet); setError(null);
    }).catch(() => setError("The conclusion export packet could not be loaded."));
  }, [projectId]);

  function download() {
    if (!packet) return;
    const blob = new Blob([JSON.stringify(packet, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `lionsforge-conclusion-${packet.content.project_id}-${packet.content_sha256.slice(0, 12)}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  if (!projectId) return <section className="dashboard-state">Create a research project before exporting a conclusion packet.</section>;
  return <section className="research-provenance-section">
    <div className="research-section-heading"><div><p className="eyebrow">RESEARCH WORKSPACE</p><h1>Conclusion export packet</h1><p className="muted">Preview and download a deterministic record of the owner-authored conclusion, cited evidence, readiness state, and revision trail.</p></div></div>
    {error ? <p role="alert" className="form-message">{error}</p> : null}
    <section className="dashboard-panel"><label>Project<select aria-label="Export packet project" value={projectId} onChange={(event) => setProjectId(Number(event.target.value))}>{projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}</select></label></section>
    {packet ? <>
      <section className="dashboard-panel"><h2>{packet.content.project_title}</h2><p>Status: {packet.content.conclusion_status}</p><p>Schema: {packet.content.schema_version}</p><p>SHA-256: <code>{packet.content_sha256}</code></p><p>Generated: {new Date(packet.generated_at).toLocaleString()}</p><button type="button" onClick={download}>Download JSON packet</button></section>
      <section className="dashboard-panel"><h2>Readiness: {packet.content.readiness.state.replaceAll("_", " ")}</h2><p>{packet.content.readiness.blocking_count} blocking · {packet.content.readiness.caution_count} caution</p><ul>{packet.content.readiness.next_steps.map((step) => <li key={step}>{step}</li>)}</ul><p className="muted">{packet.content.readiness.disclaimer}</p></section>
      <section className="dashboard-panel"><h2>Owner-authored conclusion</h2><p>{packet.content.conclusion_text || "No conclusion has been authored for this project."}</p></section>
      <section className="dashboard-panel"><h2>Cited evidence ({packet.content.evidence.length})</h2>{packet.content.evidence.map((item) => <article key={item.id}><strong>Evidence {item.id}: {item.source_title}</strong><p>{item.claim}</p><p>{item.validation_status}</p></article>)}</section>
      <section className="dashboard-panel"><h2>Revision trail ({packet.content.revisions.length})</h2>{packet.content.revisions.map((item) => <article key={item.revision_number}><strong>Revision {item.revision_number} · {item.status}</strong><p>{item.revision_note ?? "No revision note"} · {new Date(item.created_at).toLocaleString()}</p></article>)}</section>
      <p className="muted">{packet.content.disclaimer}</p>
    </> : null}
  </section>;
}
