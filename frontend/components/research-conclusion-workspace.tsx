"use client";

import { useEffect, useState } from "react";
import type { ResearchProject } from "@/lib/research";

type Evidence = { id: number; source_title: string; claim: string; validation_status: string };
type Revision = { id: number; revision_number: number; status: string; revision_note: string | null; created_at: string };
type Workspace = { project_id: number; status: "draft" | "revised" | "finalized"; conclusion_text: string; evidence_ids: number[]; revision_count: number; revisions: Revision[]; disclaimer: string };
type Readiness = { state: string; blocking_count: number; caution_count: number; next_steps: string[]; disclaimer: string };

export function ResearchConclusionWorkspace() {
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [text, setText] = useState("");
  const [selected, setSelected] = useState<number[]>([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetch("/api/research-projects", { cache: "no-store" }).then(async (response) => {
      if (response.status === 401) { window.location.href = "/login"; return; }
      if (!response.ok) throw new Error();
      const body = await response.json() as ResearchProject[];
      setProjects(body); setProjectId(body[0]?.id ?? null);
    }).catch(() => setError("Research projects could not be loaded."));
  }, []);

  async function load(id: number) {
    const [workspaceResponse, readinessResponse, evidenceResponse] = await Promise.all([
      fetch(`/api/research-conclusion-workspace/${id}`, { cache: "no-store" }),
      fetch(`/api/research-conclusion-readiness/${id}`, { cache: "no-store" }),
      fetch(`/api/research-conclusion-evidence/${id}`, { cache: "no-store" }),
    ]);
    if ([workspaceResponse, readinessResponse, evidenceResponse].some((response) => response.status === 401)) { window.location.href = "/login"; return; }
    if (!workspaceResponse.ok || !readinessResponse.ok || !evidenceResponse.ok) throw new Error();
    const nextWorkspace = await workspaceResponse.json() as Workspace;
    setWorkspace(nextWorkspace); setText(nextWorkspace.conclusion_text); setSelected(nextWorkspace.evidence_ids);
    setReadiness(await readinessResponse.json() as Readiness);
    setEvidence(await evidenceResponse.json() as Evidence[]);
  }

  useEffect(() => { if (projectId) void load(projectId).catch(() => setError("The conclusion workspace could not be loaded.")); }, [projectId]);

  async function save(finalize: boolean) {
    if (!projectId) return;
    if (finalize && !window.confirm("Finalize this user-authored conclusion? This does not certify truth or accuracy.")) return;
    const response = await fetch(`/api/research-conclusion-workspace/${projectId}`, {
      method: "PUT", headers: { "content-type": "application/json" },
      body: JSON.stringify({ conclusion_text: text, evidence_ids: selected, revision_note: note || null, finalize, confirmed: finalize || workspace?.status === "finalized" }),
    });
    if (!response.ok) { setError("The conclusion could not be saved."); return; }
    setWorkspace(await response.json() as Workspace); setNote("");
  }

  if (!projectId) return <section className="dashboard-state">Create a research project before drafting a conclusion.</section>;
  return <section className="research-provenance-section">
    <div className="research-section-heading"><div><p className="eyebrow">RESEARCH WORKSPACE</p><h1>User-authored conclusion</h1><p className="muted">Draft and revise your conclusion while retaining explicit evidence references and revision history.</p></div></div>
    {error ? <p role="alert" className="form-message">{error}</p> : null}
    <section className="dashboard-panel"><label>Project<select aria-label="Conclusion project" value={projectId} onChange={(event) => setProjectId(Number(event.target.value))}>{projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}</select></label></section>
    {readiness ? <section className="dashboard-panel" aria-label="Conclusion readiness warning"><h2>Readiness: {readiness.state.replaceAll("_", " ")}</h2><p>{readiness.blocking_count} blocking · {readiness.caution_count} caution</p><ul>{readiness.next_steps.map((step) => <li key={step}>{step}</li>)}</ul><p className="muted">{readiness.disclaimer}</p></section> : null}
    <section className="dashboard-panel"><label>Conclusion<textarea aria-label="Conclusion text" value={text} onChange={(event) => setText(event.target.value)} rows={12} maxLength={20000} /></label><label>Revision note<input aria-label="Revision note" value={note} onChange={(event) => setNote(event.target.value)} maxLength={1000} /></label></section>
    <section className="dashboard-panel"><h2>Evidence references</h2>{evidence.map((item) => <label key={item.id}><input type="checkbox" checked={selected.includes(item.id)} onChange={(event) => setSelected(event.target.checked ? [...selected, item.id] : selected.filter((id) => id !== item.id))} /> Evidence {item.id}: {item.source_title} — {item.claim} ({item.validation_status})</label>)}{!evidence.length ? <p>No evidence records are available for this project.</p> : null}</section>
    <div><button type="button" onClick={() => void save(false)}>Save draft</button><button type="button" onClick={() => void save(true)}>Finalize conclusion</button></div>
    <section className="dashboard-panel"><h2>Revision history ({workspace?.revision_count ?? 0})</h2>{workspace?.revisions.map((revision) => <article key={revision.id}><strong>Revision {revision.revision_number} · {revision.status}</strong><p>{revision.revision_note ?? "No revision note"} · {new Date(revision.created_at).toLocaleString()}</p></article>)}</section>
    <p className="muted">{workspace?.disclaimer}</p>
  </section>;
}
