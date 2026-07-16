"use client";

import { useEffect, useMemo, useState } from "react";

import type { ResearchProject } from "@/lib/research";

type ImpactLevel = "high_attention" | "review_required" | "informational";
type Preference = { id: number; project_ids: number[]; impact_levels: ImpactLevel[]; window_days: number; cadence: "daily" | "weekly" | "monthly"; created_at: string; updated_at: string };
type DigestItem = { category: string; action_id: number; project_id: number; evidence_id: number; impact_level: ImpactLevel; governing_rule: string; status: string; reason: string; action_text: string; supporting_event_ids: string[]; age_days: number; reopen_count: number };
type Digest = { generated_at: string; window_start: string; window_end: string; summary: { newly_opened: number; overdue: number; reopened: number; deferred: number; recently_resolved: number; total_items: number }; items: DigestItem[]; content_sha256: string; disclaimer: string };
type History = { snapshots: { id: number; generated_at: string; content_sha256: string; item_count: number; summary: Record<string, number> }[] };

const allImpacts: ImpactLevel[] = ["high_attention", "review_required", "informational"];

export function ResearchGovernanceDigest() {
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [projectIds, setProjectIds] = useState<number[]>([]);
  const [impactLevels, setImpactLevels] = useState<ImpactLevel[]>(allImpacts);
  const [windowDays, setWindowDays] = useState(30);
  const [cadence, setCadence] = useState<Preference["cadence"]>("weekly");
  const [digest, setDigest] = useState<Digest | null>(null);
  const [history, setHistory] = useState<History>({ snapshots: [] });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const [projectsResponse, preferencesResponse, historyResponse] = await Promise.all([
          fetch("/api/research-projects", { cache: "no-store", signal: controller.signal }),
          fetch("/api/research-governance-digest/preferences", { cache: "no-store", signal: controller.signal }),
          fetch("/api/research-governance-digest/history", { cache: "no-store", signal: controller.signal }),
        ]);
        if ([projectsResponse, preferencesResponse, historyResponse].some((response) => response.status === 401)) { window.location.href = "/login"; return; }
        if (!projectsResponse.ok || !preferencesResponse.ok || !historyResponse.ok) { setError("Governance digest settings could not be loaded."); return; }
        const loadedProjects = (await projectsResponse.json()) as ResearchProject[];
        const preference = (await preferencesResponse.json()) as Preference | null;
        setProjects(loadedProjects);
        setProjectIds(preference?.project_ids ?? loadedProjects.map((project) => project.id));
        setImpactLevels(preference?.impact_levels ?? allImpacts);
        setWindowDays(preference?.window_days ?? 30);
        setCadence(preference?.cadence ?? "weekly");
        setHistory((await historyResponse.json()) as History);
      } catch (requestError) {
        if (!(requestError instanceof DOMException && requestError.name === "AbortError")) setError("The governance digest workspace is unavailable.");
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  const selectedProjectNames = useMemo(() => projects.filter((project) => projectIds.includes(project.id)).map((project) => project.title), [projects, projectIds]);

  async function savePreferences() {
    setBusy(true); setError(null);
    try {
      const response = await fetch("/api/research-governance-digest/preferences", { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify({ project_ids: projectIds, impact_levels: impactLevels, window_days: windowDays, cadence }) });
      if (response.status === 401) { window.location.href = "/login"; return; }
      if (!response.ok) { setError("Digest preferences could not be saved."); return; }
    } finally { setBusy(false); }
  }

  async function preview() {
    setBusy(true); setError(null);
    try {
      const query = new URLSearchParams();
      projectIds.forEach((id) => query.append("project_ids", String(id)));
      impactLevels.forEach((level) => query.append("impact_levels", level));
      query.set("window_days", String(windowDays));
      const response = await fetch(`/api/research-governance-digest/preview?${query}`, { cache: "no-store" });
      if (response.status === 401) { window.location.href = "/login"; return; }
      if (!response.ok) { setError("The governance digest could not be previewed."); return; }
      setDigest((await response.json()) as Digest);
    } finally { setBusy(false); }
  }

  async function generate() {
    await savePreferences();
    setBusy(true); setError(null);
    try {
      const response = await fetch("/api/research-governance-digest/generate", { method: "POST" });
      if (!response.ok) { setError("The governance digest snapshot could not be generated."); return; }
      setDigest((await response.json()) as Digest);
      const refreshed = await fetch("/api/research-governance-digest/history", { cache: "no-store" });
      if (refreshed.ok) setHistory((await refreshed.json()) as History);
    } finally { setBusy(false); }
  }

  return <section className="research-provenance-section">
    <div className="research-section-heading"><div><p className="eyebrow">RESEARCH WORKSPACE</p><h2>Governance review digest</h2><p className="muted">Preview and preserve deterministic workflow summaries without changing evidence or action state.</p></div></div>
    {error ? <p role="alert" className="form-message">{error}</p> : null}
    <section className="dashboard-panel" aria-labelledby="digest-preferences-title"><div className="panel-heading"><div><p className="eyebrow">DIGEST PREFERENCES</p><h3 id="digest-preferences-title">Projects, impact, window, and cadence</h3></div></div>
      <div className="form-grid"><fieldset><legend>Projects</legend>{projects.map((project) => <label key={project.id}><input type="checkbox" checked={projectIds.includes(project.id)} onChange={() => setProjectIds((current) => current.includes(project.id) ? current.filter((id) => id !== project.id) : [...current, project.id].sort((a, b) => a - b))} />{project.title}</label>)}</fieldset><fieldset><legend>Impact levels</legend>{allImpacts.map((level) => <label key={level}><input type="checkbox" checked={impactLevels.includes(level)} onChange={() => setImpactLevels((current) => current.includes(level) ? current.filter((item) => item !== level) : [...current, level])} />{level.replaceAll("_", " ")}</label>)}</fieldset><label>Window<select aria-label="Digest time window" value={windowDays} onChange={(event) => setWindowDays(Number(event.target.value))}><option value={7}>7 days</option><option value={30}>30 days</option><option value={90}>90 days</option><option value={365}>365 days</option></select></label><label>Cadence metadata<select aria-label="Digest cadence" value={cadence} onChange={(event) => setCadence(event.target.value as Preference["cadence"])}><option value="daily">Daily</option><option value="weekly">Weekly</option><option value="monthly">Monthly</option></select></label></div>
      <p className="muted"><strong>Included:</strong> {selectedProjectNames.join(", ") || "No projects"}</p><button type="button" disabled={busy || !projectIds.length || !impactLevels.length} onClick={() => void savePreferences()}>Save preferences</button><button type="button" disabled={busy || !projectIds.length || !impactLevels.length} onClick={() => void preview()}>Preview digest</button><button type="button" disabled={busy || !projectIds.length || !impactLevels.length} onClick={() => void generate()}>Generate snapshot</button>
    </section>
    {digest ? <section className="dashboard-panel" aria-labelledby="digest-preview-title"><div className="panel-heading"><div><p className="eyebrow">DIGEST PREVIEW</p><h3 id="digest-preview-title">Governance items requiring context</h3><p className="muted">{digest.disclaimer}</p></div></div><div className="metric-grid"><article><strong>{digest.summary.overdue}</strong><span>Overdue</span></article><article><strong>{digest.summary.reopened}</strong><span>Reopened</span></article><article><strong>{digest.summary.newly_opened}</strong><span>Newly opened</span></article><article><strong>{digest.summary.deferred}</strong><span>Deferred</span></article><article><strong>{digest.summary.recently_resolved}</strong><span>Recently resolved</span></article></div><div className="activity-list">{digest.items.map((item) => <article className="activity-card" key={`${item.category}-${item.action_id}`}><span>{item.category.replaceAll("_", " ").toUpperCase()}</span><div><strong>{item.impact_level.replaceAll("_", " ")} · project {item.project_id} · action {item.action_id}</strong><p>{item.reason}</p><p><strong>Evidence:</strong> {item.evidence_id} · <strong>Rule:</strong> {item.governing_rule} · <strong>Events:</strong> {item.supporting_event_ids.join(", ")}</p><p><strong>Action:</strong> {item.action_text}</p></div></article>)}</div><p className="muted"><strong>Digest SHA-256:</strong> {digest.content_sha256}</p></section> : null}
    <section className="dashboard-panel" aria-labelledby="digest-history-title"><div className="panel-heading"><div><p className="eyebrow">DIGEST HISTORY</p><h3 id="digest-history-title">Generated metadata</h3><p className="muted">Snapshots retain only hashes and summary metadata.</p></div></div>{history.snapshots.length ? <div className="activity-list">{history.snapshots.map((snapshot) => <article className="activity-card" key={snapshot.id}><span>{snapshot.item_count} ITEMS</span><div><strong>{new Date(snapshot.generated_at).toLocaleString()}</strong><p>{snapshot.content_sha256}</p></div></article>)}</div> : <p className="muted">No digest snapshots have been generated.</p>}</section>
  </section>;
}
