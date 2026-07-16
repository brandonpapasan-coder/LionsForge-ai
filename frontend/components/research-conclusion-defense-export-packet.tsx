"use client";

import { useEffect, useState } from "react";
import type { ResearchProject } from "@/lib/research";

type Packet = {
  content_sha256: string;
  generated_at: string;
  content: {
    conclusion: { project_id: number; project_title: string; conclusion_status: string; conclusion_text: string; evidence: unknown[]; revisions: unknown[]; readiness: { state: string } };
    defense: { status: string; conclusion_revision_number: number | null; evidence_coverage: string; strongest_counterargument: string; known_limitations: string; unresolved_questions: string; confidence_rationale: string; missing_sections: string[]; revisions: { revision_number: number; status: string; revision_note: string | null; created_at: string }[] };
    disclaimer: string;
  };
};

export function ResearchConclusionDefenseExportPacket() {
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
    void fetch(`/api/research-conclusion-defense-export/${projectId}`, { cache: "no-store" }).then(async (response) => {
      if (response.status === 401) { window.location.href = "/login"; return; }
      if (!response.ok) throw new Error();
      setPacket(await response.json() as Packet); setError(null);
    }).catch(() => setError("The conclusion defense export packet could not be loaded."));
  }, [projectId]);

  function download() {
    if (!packet) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(packet, null, 2)], { type: "application/json" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `lionsforge-conclusion-defense-${packet.content.conclusion.project_id}-${packet.content_sha256.slice(0, 12)}.json`;
    anchor.click(); URL.revokeObjectURL(url);
  }

  if (!projectId) return <section className="dashboard-state">Create a research project before exporting a conclusion defense packet.</section>;
  const defense = packet?.content.defense;
  return <section className="research-provenance-section">
    <div className="research-section-heading"><div><p className="eyebrow">RESEARCH WORKSPACE</p><h1>Conclusion defense export packet</h1><p className="muted">Preview and download the user-authored conclusion, research trail, defense review, and revision history.</p></div></div>
    {error ? <p role="alert" className="form-message">{error}</p> : null}
    <section className="dashboard-panel"><label>Project<select aria-label="Conclusion defense export project" value={projectId} onChange={(event) => setProjectId(Number(event.target.value))}>{projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}</select></label></section>
    {packet && defense ? <>
      <section className="dashboard-panel"><h2>{packet.content.conclusion.project_title}</h2><p>Conclusion: {packet.content.conclusion.conclusion_status}</p><p>Defense: {defense.status}</p><p>Readiness: {packet.content.conclusion.readiness.state.replaceAll("_", " ")}</p><p>SHA-256: <code>{packet.content_sha256}</code></p><button type="button" onClick={download}>Download combined JSON packet</button></section>
      <section className="dashboard-panel"><h2>Owner-authored conclusion</h2><p>{packet.content.conclusion.conclusion_text || "No conclusion has been authored."}</p><p>{packet.content.conclusion.evidence.length} evidence records · {packet.content.conclusion.revisions.length} conclusion revisions</p></section>
      <section className="dashboard-panel"><h2>Defense review</h2>{defense.status === "missing" ? <p>No defense review has been authored.</p> : <><p>Linked conclusion revision: {defense.conclusion_revision_number ?? "None"}</p><p>Evidence coverage: {defense.evidence_coverage}</p><p>Strongest counterargument: {defense.strongest_counterargument}</p><p>Known limitations: {defense.known_limitations}</p><p>Unresolved questions: {defense.unresolved_questions}</p><p>Confidence rationale: {defense.confidence_rationale}</p>{defense.missing_sections.length ? <p>Missing: {defense.missing_sections.join(", ")}</p> : null}</>}</section>
      <section className="dashboard-panel"><h2>Defense revision trail ({defense.revisions.length})</h2>{defense.revisions.map((item) => <article key={item.revision_number}><strong>Revision {item.revision_number} · {item.status}</strong><p>{item.revision_note ?? "No revision note"}</p></article>)}</section>
      <p className="muted">{packet.content.disclaimer}</p>
    </> : null}
  </section>;
}
