"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import type { ResearchProject } from "@/lib/research";

export function ResearchWorkspace() {
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [selected, setSelected] = useState<ResearchProject | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  async function loadProjects() {
    const response = await fetch("/api/research-projects", { cache: "no-store" });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    if (!response.ok) {
      setError("Research projects could not be loaded.");
      return;
    }
    const payload = (await response.json()) as ResearchProject[];
    setProjects(payload);
    setSelected((current) => current ?? payload[0] ?? null);
  }

  useEffect(() => {
    void loadProjects();
  }, []);

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true);
    setError(null);
    const form = event.currentTarget;
    const data = new FormData(form);

    try {
      const response = await fetch("/api/research-projects", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          title: String(data.get("title") ?? "").trim(),
          description: String(data.get("description") ?? "").trim() || null,
          objective: String(data.get("objective") ?? "").trim() || null,
          context: {},
        }),
      });
      if (!response.ok) {
        setError("The research project could not be created.");
        return;
      }
      const project = (await response.json()) as ResearchProject;
      setProjects((current) => [project, ...current]);
      setSelected(project);
      form.reset();
    } catch {
      setError("The research service is unavailable.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="research-shell">
      <aside className="research-sidebar">
        <div>
          <p className="eyebrow">RESEARCH PROJECTS</p>
          <h1>Workspace</h1>
        </div>
        <div className="research-project-list">
          {projects.length ? projects.map((project) => (
            <button
              type="button"
              key={project.id}
              className={selected?.id === project.id ? "active" : ""}
              onClick={() => setSelected(project)}
            >
              <strong>{project.title}</strong>
              <span>{project.objective ?? project.description ?? "Open research project"}</span>
            </button>
          )) : <p className="muted">No research projects yet.</p>}
        </div>
      </aside>

      <main className="research-main">
        {selected ? (
          <section className="research-project-view">
            <div className="research-project-header">
              <div>
                <p className="eyebrow">ACTIVE RESEARCH</p>
                <h2>{selected.title}</h2>
                <p>{selected.objective ?? selected.description ?? "Define the objective for this project."}</p>
              </div>
              <Link className="primary-link" href={`/mentor?research_project=${selected.id}`}>Ask AI Mentor</Link>
            </div>

            <div className="research-card-grid">
              <article>
                <span>Status</span>
                <strong>{selected.status}</strong>
                <p>Current project lifecycle state.</p>
              </article>
              <article>
                <span>Last updated</span>
                <strong>{new Date(selected.updated_at).toLocaleDateString()}</strong>
                <p>Most recent saved project change.</p>
              </article>
            </div>

            <section className="research-notebook">
              <div>
                <p className="eyebrow">RESEARCH NOTEBOOK</p>
                <h3>Structure the investigation</h3>
              </div>
              <div className="research-notebook-grid">
                <article><strong>Thesis</strong><p>State the current working conclusion.</p></article>
                <article><strong>Evidence</strong><p>Collect supporting and contradicting sources.</p></article>
                <article><strong>Risks</strong><p>Record uncertainty, assumptions, and failure conditions.</p></article>
                <article><strong>Decision Journal</strong><p>Track what changed your confidence and why.</p></article>
              </div>
            </section>
          </section>
        ) : (
          <section className="research-empty">
            <h2>Create your first research project</h2>
            <p>Start with a clear question, objective, and evidence trail.</p>
          </section>
        )}

        <section className="research-create-panel">
          <div>
            <p className="eyebrow">NEW PROJECT</p>
            <h3>Begin a structured investigation</h3>
          </div>
          <form onSubmit={createProject}>
            <label>Title<input name="title" required maxLength={160} /></label>
            <label>Description<textarea name="description" /></label>
            <label>Objective<textarea name="objective" /></label>
            <button type="submit" disabled={creating}>{creating ? "Creating…" : "Create project"}</button>
          </form>
          {error ? <p role="alert" className="form-message">{error}</p> : null}
        </section>
      </main>
    </div>
  );
}
