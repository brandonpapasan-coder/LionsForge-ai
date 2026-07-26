"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import type { ResearchProject, ResearchSession } from "@/lib/research";
import {
  type PracticumEnrollment,
  type PracticumReadiness,
  type PracticumTemplate,
  type ResearchEvidenceOption,
  researchPracticumClient,
} from "@/lib/research-practicum";

export function ResearchPracticumWorkspace() {
  const [templates, setTemplates] = useState<PracticumTemplate[]>([]);
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [enrollments, setEnrollments] = useState<PracticumEnrollment[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [readiness, setReadiness] = useState<PracticumReadiness | null>(null);
  const [evidence, setEvidence] = useState<ResearchEvidenceOption[]>([]);
  const [evidenceQuery, setEvidenceQuery] = useState("");
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const selected = enrollments.find((item) => item.id === selectedId) ?? enrollments[0] ?? null;
  const template = templates.find((item) => item.slug === selected?.template_slug) ?? null;
  const selectedProject = projects.find((item) => item.id === selected?.research_project_id) ?? null;
  const filteredEvidence = useMemo(() => {
    const query = evidenceQuery.trim().toLowerCase();
    if (!query) return evidence;
    return evidence.filter((item) =>
      `${item.title} ${item.source_type} ${item.tags.join(" ")}`.toLowerCase().includes(query),
    );
  }, [evidence, evidenceQuery]);

  const reload = useCallback(async () => {
    setError(null);
    try {
      const [templateData, enrollmentData, projectResponse] = await Promise.all([
        researchPracticumClient.templates(),
        researchPracticumClient.enrollments(),
        fetch("/api/research-projects", { cache: "no-store" }),
      ]);
      if (projectResponse.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!projectResponse.ok) throw new Error("Research projects could not be loaded.");
      setTemplates(templateData);
      setEnrollments(enrollmentData);
      setProjects((await projectResponse.json()) as ResearchProject[]);
      setSelectedId((current) => current ?? enrollmentData[0]?.id ?? null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Research practica could not be loaded.");
    }
  }, []);

  useEffect(() => { void reload(); }, [reload]);

  useEffect(() => {
    if (!selected) {
      setReadiness(null);
      return;
    }
    void researchPracticumClient.readiness(selected.id).then(setReadiness).catch(() => setReadiness(null));
  }, [selected?.id, selected?.updated_at]);

  useEffect(() => {
    if (!selected) {
      setEvidence([]);
      return;
    }
    const controller = new AbortController();
    async function loadEvidence() {
      setEvidenceLoading(true);
      try {
        const sessionsResponse = await fetch(`/api/research-projects/${selected.research_project_id}/sessions`, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (!sessionsResponse.ok) throw new Error("Project evidence could not be loaded.");
        const sessions = (await sessionsResponse.json()) as ResearchSession[];
        const evidenceResponses = await Promise.all(
          sessions.map((session) => fetch(`/api/research-sessions/${session.id}/evidence`, {
            cache: "no-store",
            signal: controller.signal,
          })),
        );
        if (evidenceResponses.some((response) => !response.ok)) throw new Error("Project evidence could not be loaded.");
        const evidenceGroups = await Promise.all(evidenceResponses.map((response) => response.json() as Promise<ResearchEvidenceOption[]>));
        if (!controller.signal.aborted) setEvidence(evidenceGroups.flat());
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setEvidence([]);
          setError(requestError instanceof Error ? requestError.message : "Project evidence could not be loaded.");
        }
      } finally {
        if (!controller.signal.aborted) setEvidenceLoading(false);
      }
    }
    void loadEvidence();
    return () => controller.abort();
  }, [selected?.research_project_id, selected?.updated_at]);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await reload();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "The practicum action failed.");
    } finally {
      setBusy(false);
    }
  }

  async function enroll(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    await run(() => researchPracticumClient.createEnrollment(String(data.get("template")), Number(data.get("project"))));
  }

  const locked = busy || selected?.status === "review_ready" || selected?.status === "completed";

  return (
    <section className="lesson-card" aria-labelledby="research-practicum-heading">
      <div className="lesson-meta"><span>applied research</span><span>{enrollments.length} practica</span></div>
      <h2 id="research-practicum-heading">Research practicum</h2>
      <p>Demonstrate research competencies through project evidence, learner-authored reflection, deterministic readiness checks, and explicit human review.</p>
      {error ? <p role="alert">{error}</p> : null}

      {templates.length > 0 && projects.length > 0 ? (
        <form onSubmit={enroll} className="practicum-form-grid">
          <label>Practicum template<select name="template" required>{templates.map((item) => <option key={`${item.slug}:${item.version}`} value={item.slug}>{item.title}</option>)}</select></label>
          <label>Linked research project<select name="project" required>{projects.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
          <button disabled={busy} type="submit">Start practicum</button>
        </form>
      ) : <p>Create a research project and complete prerequisite lessons to begin a practicum.</p>}

      {enrollments.length > 1 ? (
        <label>Active practicum<select value={selected?.id ?? ""} onChange={(event) => setSelectedId(Number(event.target.value))}>{enrollments.map((item) => <option key={item.id} value={item.id}>{item.template_slug.replaceAll("-", " ")} · {item.status.replaceAll("_", " ")}</option>)}</select></label>
      ) : null}

      {selected && template ? (
        <article>
          <div className="lesson-meta"><span>{template.title}</span><span>{selected.status.replaceAll("_", " ")}</span></div>
          <p>Linked project: <strong>{selectedProject?.title ?? `Project ${selected.research_project_id}`}</strong></p>
          <div role="search" aria-label="Search linked project evidence">
            <label htmlFor="practicum-evidence-search">Search project evidence</label>
            <input
              id="practicum-evidence-search"
              type="search"
              value={evidenceQuery}
              onChange={(event) => setEvidenceQuery(event.target.value)}
              placeholder="Search by title, category, or tag"
            />
            <p role="status" aria-live="polite">
              {evidenceLoading ? "Loading project evidence…" : `${filteredEvidence.length} evidence record${filteredEvidence.length === 1 ? "" : "s"} available.`}
            </p>
          </div>

          {template.objectives.map((objective) => {
            const progress = selected.objectives.find((item) => item.objective_key === objective.objective_key);
            const objectiveReadiness = readiness?.objectives.find((item) => item.objective_key === objective.objective_key);
            const attachedIds = new Set(progress?.evidence_references.map((reference) => reference.research_evidence_id) ?? []);
            const availableEvidence = filteredEvidence.filter((item) => !attachedIds.has(item.id));
            return (
              <section key={objective.objective_key} aria-labelledby={`objective-${objective.objective_key}`}>
                <h3 id={`objective-${objective.objective_key}`}>{objective.sequence}. {objective.title}</h3>
                <p>{objective.description}</p>
                <p>Evidence requirements: {objective.required_evidence_categories.join(", ")} · minimum {objective.minimum_evidence_count}</p>
                <form onSubmit={(event) => {
                  event.preventDefault();
                  const data = new FormData(event.currentTarget);
                  void run(() => researchPracticumClient.updateReflection(selected.id, objective.objective_key, String(data.get("reflection") ?? "")));
                }}>
                  <label>Learner reflection<textarea name="reflection" defaultValue={progress?.reflection ?? ""} disabled={locked} /></label>
                  <button disabled={locked} type="submit">Save reflection</button>
                </form>
                <form onSubmit={(event) => {
                  event.preventDefault();
                  const data = new FormData(event.currentTarget);
                  void run(() => researchPracticumClient.attachEvidence(selected.id, objective.objective_key, Number(data.get("evidenceId"))));
                }}>
                  <label>
                    Project evidence
                    <select name="evidenceId" disabled={locked || evidenceLoading || availableEvidence.length === 0} required defaultValue="">
                      <option value="" disabled>Select evidence</option>
                      {availableEvidence.map((item) => (
                        <option key={item.id} value={item.id}>{item.title} · {item.source_type.replaceAll("_", " ")}</option>
                      ))}
                    </select>
                  </label>
                  <button disabled={locked || evidenceLoading || availableEvidence.length === 0} type="submit">Attach evidence</button>
                </form>
                {availableEvidence.length === 0 && !evidenceLoading ? <p>No additional matching evidence is available for this objective.</p> : null}
                {progress?.evidence_references.map((reference) => {
                  const record = evidence.find((item) => item.id === reference.research_evidence_id);
                  return (
                    <p key={reference.id}>
                      {record?.title ?? `Evidence #${reference.research_evidence_id}`}
                      {record ? ` · ${record.source_type.replaceAll("_", " ")}` : ""}{" "}
                      <button disabled={locked} type="button" onClick={() => void run(() => researchPracticumClient.removeEvidence(selected.id, objective.objective_key, reference.id))}>Remove reference</button>
                    </p>
                  );
                })}
                <p>Status: {objectiveReadiness?.status.replaceAll("_", " ") ?? "checking"}</p>
                {objectiveReadiness?.missing_requirements.length ? <p>Missing: {objectiveReadiness.missing_requirements.join("; ")}</p> : null}
              </section>
            );
          })}

          {readiness ? (
            <aside aria-label="Practicum readiness">
              <h3>Readiness summary</h3>
              <p>{readiness.advisory_notice}</p>
              <p>{readiness.ready_for_human_review ? "Ready for human review." : `Missing requirements: ${readiness.missing_requirements.join("; ") || "none"}`}</p>
              <button disabled={busy || !readiness.ready_for_human_review || selected.status === "review_ready" || selected.status === "completed"} type="button" onClick={() => void run(() => researchPracticumClient.submit(selected.id))}>Submit for review</button>
            </aside>
          ) : null}

          <h3>Human review history</h3>
          {selected.review_history.length === 0 ? <p>No human review decisions yet.</p> : selected.review_history.map((review) => <p key={review.id}><strong>{review.decision.replaceAll("_", " ")}</strong> · {review.notes ?? "No notes"}</p>)}
        </article>
      ) : <p>No active practicum enrollment yet.</p>}
    </section>
  );
}
