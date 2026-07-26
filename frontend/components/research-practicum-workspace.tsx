"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import type { ResearchProject } from "@/lib/research";
import {
  type PracticumEnrollment,
  type PracticumReadiness,
  type PracticumTemplate,
  researchPracticumClient,
} from "@/lib/research-practicum";

export function ResearchPracticumWorkspace() {
  const [templates, setTemplates] = useState<PracticumTemplate[]>([]);
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [enrollments, setEnrollments] = useState<PracticumEnrollment[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [readiness, setReadiness] = useState<PracticumReadiness | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const selected = enrollments.find((item) => item.id === selectedId) ?? enrollments[0] ?? null;
  const template = templates.find((item) => item.slug === selected?.template_slug) ?? null;

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

  return (
    <section className="lesson-card" aria-label="Research practicum">
      <div className="lesson-meta"><span>applied research</span><span>{enrollments.length} practica</span></div>
      <h2>Research practicum</h2>
      <p>Demonstrate research competencies through project evidence, learner-authored reflection, deterministic readiness checks, and explicit human review.</p>
      {error ? <p role="alert">{error}</p> : null}

      {templates.length > 0 && projects.length > 0 ? (
        <form onSubmit={enroll}>
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
          <p>Linked project ID: {selected.research_project_id}</p>
          {template.objectives.map((objective) => {
            const progress = selected.objectives.find((item) => item.objective_key === objective.objective_key);
            const objectiveReadiness = readiness?.objectives.find((item) => item.objective_key === objective.objective_key);
            return (
              <section key={objective.objective_key} aria-label={objective.title}>
                <h3>{objective.sequence}. {objective.title}</h3>
                <p>{objective.description}</p>
                <p>Evidence requirements: {objective.required_evidence_categories.join(", ")} · minimum {objective.minimum_evidence_count}</p>
                <form onSubmit={(event) => {
                  event.preventDefault();
                  const data = new FormData(event.currentTarget);
                  void run(() => researchPracticumClient.updateReflection(selected.id, objective.objective_key, String(data.get("reflection") ?? "")));
                }}>
                  <label>Learner reflection<textarea name="reflection" defaultValue={progress?.reflection ?? ""} disabled={busy || selected.status === "review_ready" || selected.status === "completed"} /></label>
                  <button disabled={busy || selected.status === "review_ready" || selected.status === "completed"} type="submit">Save reflection</button>
                </form>
                <form onSubmit={(event) => {
                  event.preventDefault();
                  const data = new FormData(event.currentTarget);
                  void run(() => researchPracticumClient.attachEvidence(selected.id, objective.objective_key, Number(data.get("evidenceId"))));
                }}>
                  <label>Research evidence ID<input name="evidenceId" min="1" type="number" required /></label>
                  <button disabled={busy || selected.status === "review_ready" || selected.status === "completed"} type="submit">Attach evidence</button>
                </form>
                {progress?.evidence_references.map((reference) => (
                  <p key={reference.id}>Evidence #{reference.research_evidence_id} <button disabled={busy || selected.status === "review_ready" || selected.status === "completed"} type="button" onClick={() => void run(() => researchPracticumClient.removeEvidence(selected.id, objective.objective_key, reference.id))}>Remove reference</button></p>
                ))}
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
