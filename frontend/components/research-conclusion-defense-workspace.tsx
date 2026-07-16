"use client";

import { useEffect, useState } from "react";
import type { ResearchProject } from "@/lib/research";

type Evidence = { id: number; source_title: string; claim: string; validation_status: string };
type ConclusionRevision = { revision_number: number; status: string; created_at: string };
type Conclusion = { revisions: ConclusionRevision[] };
type DefenseRevision = { id: number; revision_number: number; status: string; missing_sections: string[]; revision_note: string | null; created_at: string };
type Defense = {
  project_id: number;
  conclusion_revision_number: number | null;
  evidence_ids: number[];
  evidence_coverage: string;
  strongest_counterargument: string;
  known_limitations: string;
  unresolved_questions: string;
  confidence_rationale: string;
  status: "incomplete" | "complete";
  missing_sections: string[];
  revision_count: number;
  revisions: DefenseRevision[];
  disclaimer: string;
};

type Fields = Pick<Defense, "evidence_coverage" | "strongest_counterargument" | "known_limitations" | "unresolved_questions" | "confidence_rationale">;
const EMPTY: Fields = { evidence_coverage: "", strongest_counterargument: "", known_limitations: "", unresolved_questions: "", confidence_rationale: "" };
const LABELS: Record<keyof Fields, string> = {
  evidence_coverage: "Evidence coverage",
  strongest_counterargument: "Strongest counterargument",
  known_limitations: "Known limitations",
  unresolved_questions: "Unresolved questions",
  confidence_rationale: "Confidence rationale",
};

export function ResearchConclusionDefenseWorkspace() {
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [defense, setDefense] = useState<Defense | null>(null);
  const [conclusion, setConclusion] = useState<Conclusion | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [fields, setFields] = useState<Fields>(EMPTY);
  const [selectedEvidence, setSelectedEvidence] = useState<number[]>([]);
  const [revisionNumber, setRevisionNumber] = useState<number | null>(null);
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
    setDefense(null);
    const [defenseResponse, conclusionResponse, evidenceResponse] = await Promise.all([
      fetch(`/api/research-conclusion-defense/${id}`, { cache: "no-store" }),
      fetch(`/api/research-conclusion-workspace/${id}`, { cache: "no-store" }),
      fetch(`/api/research-conclusion-evidence/${id}`, { cache: "no-store" }),
    ]);
    if ([defenseResponse, conclusionResponse, evidenceResponse].some((response) => response.status === 401)) { window.location.href = "/login"; return; }
    if (!defenseResponse.ok || !conclusionResponse.ok || !evidenceResponse.ok) throw new Error();
    const nextDefense = await defenseResponse.json() as Defense;
    setDefense(nextDefense);
    setFields({ evidence_coverage: nextDefense.evidence_coverage, strongest_counterargument: nextDefense.strongest_counterargument, known_limitations: nextDefense.known_limitations, unresolved_questions: nextDefense.unresolved_questions, confidence_rationale: nextDefense.confidence_rationale });
    setSelectedEvidence(nextDefense.evidence_ids);
    setRevisionNumber(nextDefense.conclusion_revision_number);
    setConclusion(await conclusionResponse.json() as Conclusion);
    setEvidence(await evidenceResponse.json() as Evidence[]);
    setError(null);
  }

  useEffect(() => { if (projectId) void load(projectId).catch(() => setError("The defense review could not be loaded.")); }, [projectId]);

  async function save() {
    if (!projectId) return;
    const response = await fetch(`/api/research-conclusion-defense/${projectId}`, {
      method: "PUT", headers: { "content-type": "application/json" },
      body: JSON.stringify({ ...fields, evidence_ids: selectedEvidence, conclusion_revision_number: revisionNumber, revision_note: note || null }),
    });
    if (!response.ok) { setError("The defense review could not be saved."); return; }
    const next = await response.json() as Defense;
    setDefense(next); setNote(""); setError(null);
  }

  if (!projectId) return <section className="dashboard-state">Create a research project before reviewing a conclusion.</section>;
  return <section className="research-provenance-section">
    <div className="research-section-heading"><div><p className="eyebrow">RESEARCH WORKSPACE</p><h1>Conclusion defense review</h1><p className="muted">Critically examine your own conclusion. LionsForge records your reflection but does not grade or certify it.</p></div></div>
    {error ? <p role="alert" className="form-message">{error}</p> : null}
    <section className="dashboard-panel"><label>Project<select aria-label="Defense project" value={projectId} onChange={(event) => setProjectId(Number(event.target.value))}>{projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}</select></label></section>
    <section className="dashboard-panel" aria-label="Defense completeness">{defense ? <><h2>Completeness: {defense.status}</h2>{defense.missing_sections.length ? <p>Missing: {defense.missing_sections.map((item) => LABELS[item as keyof Fields] ?? item).join(", ")}</p> : <p>All reflection sections are supplied.</p>}<p className="muted">Completeness reflects supplied fields only.</p></> : <p>Loading defense review…</p>}</section>
    <section className="dashboard-panel"><label>Conclusion revision<select aria-label="Conclusion revision" value={revisionNumber ?? ""} onChange={(event) => setRevisionNumber(event.target.value ? Number(event.target.value) : null)}><option value="">No revision selected</option>{conclusion?.revisions.map((revision) => <option key={revision.revision_number} value={revision.revision_number}>Revision {revision.revision_number} · {revision.status}</option>)}</select></label></section>
    <section className="dashboard-panel"><h2>Evidence reviewed</h2>{evidence.map((item) => <label key={item.id}><input type="checkbox" checked={selectedEvidence.includes(item.id)} onChange={(event) => setSelectedEvidence(event.target.checked ? [...selectedEvidence, item.id] : selectedEvidence.filter((id) => id !== item.id))} /> Evidence {item.id}: {item.source_title} — {item.claim} ({item.validation_status})</label>)}{!evidence.length ? <p>No evidence records are available.</p> : null}</section>
    <section className="dashboard-panel">{(Object.keys(LABELS) as (keyof Fields)[]).map((key) => <label key={key}>{LABELS[key]}<textarea aria-label={LABELS[key]} rows={5} maxLength={10000} value={fields[key]} onChange={(event) => setFields({ ...fields, [key]: event.target.value })} /></label>)}<label>Revision note<input aria-label="Defense revision note" maxLength={1000} value={note} onChange={(event) => setNote(event.target.value)} /></label></section>
    <button type="button" onClick={() => void save()}>Save defense review</button>
    <section className="dashboard-panel"><h2>Defense revision history ({defense?.revision_count ?? 0})</h2>{defense?.revisions.map((revision) => <article key={revision.id}><strong>Revision {revision.revision_number} · {revision.status}</strong><p>{revision.revision_note ?? "No revision note"} · {new Date(revision.created_at).toLocaleString()}</p>{revision.missing_sections.length ? <p>Missing: {revision.missing_sections.join(", ")}</p> : null}</article>)}</section>
    <p className="muted">{defense?.disclaimer}</p>
  </section>;
}
