"use client";

import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";

import { ResearchNotebookEditor } from "@/components/research-notebook-editor";
import type { ResearchProject, ResearchSession } from "@/lib/research";

export function ResearchWorkspace() {
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [selected, setSelected] = useState<ResearchProject | null>(null);
  const [sessions, setSessions] = useState<ResearchSession[]>([]);
  const [activeSession, setActiveSession] = useState<ResearchSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creatingProject, setCreatingProject] = useState(false);
  const [creatingSession, setCreatingSession] = useState(false);
  const projectsRequest = useRef<AbortController | null>(null);
  const sessionsRequest = useRef<AbortController | null>(null);

  async function loadSessions(projectId: number) {
    sessionsRequest.current?.abort();
    const controller = new AbortController();
    sessionsRequest.current = controller;

    try {
      const response = await fetch(`/api/research-projects/${projectId}/sessions`, {
        cache: "no-store",
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      if (!response.ok) {
        setError("Research sessions could not be loaded.");
        return;
      }
      const payload = (await response.json()) as ResearchSession[];
      if (controller.signal.aborted || sessionsRequest.current !== controller) return;
      setSessions(payload);
      setActiveSession(payload[0] ?? null);
    } catch (requestError) {
      if (requestError instanceof DOMException && requestError.name === "AbortError") return;
      if (!controller.signal.aborted && sessionsRequest.current === controller) {
        setError("Research sessions could not be loaded.");
      }
    } finally {
      if (sessionsRequest.current === controller) sessionsRequest.current = null;
    }
  }

  function selectProject(project: ResearchProject) {
    setSelected(project);
    setSessions([]);
    setActiveSession(null);
    setError(null);
    void loadSessions(project.id);
  }

  function updateProject(savedProject: ResearchProject) {
    setSelected(savedProject);
    setProjects((current) => current.map((project) => (
      project.id === savedProject.id ? savedProject : project
    )));
  }

  useEffect(() => {
    const controller = new AbortController();
    projectsRequest.current = controller;

    async function loadProjects() {
      try {
        const response = await fetch("/api/research-projects", {
          cache: "no-store",
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) {
          setError("Research projects could not be loaded.");
          return;
        }
        const payload = (await response.json()) as ResearchProject[];
        if (controller.signal.aborted) return;
        setProjects(payload);
        if (payload[0]) selectProject(payload[0]);
      } catch (requestError) {
        if (requestError instanceof DOMException && requestError.name === "AbortError") return;
        if (!controller.signal.aborted) setError("Research projects could not be loaded.");
      } finally {
        if (projectsRequest.current === controller) projectsRequest.current = null;
      }
    }

    void loadProjects();
    return () => {
      controller.abort();
      projectsRequest.current = null;
      sessionsRequest.current?.abort();
      sessionsRequest.current = null;
    };
  }, []);

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreatingProject(true);
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
      sessionsRequest.current?.abort();
      setProjects((current) => [project, ...current]);
      setSelected(project);
      setSessions([]);
      setActiveSession(null);
      form.reset();
    } catch {
      setError("The research service is unavailable.");
    } finally {
      setCreatingProject(false);
    }
  }

  async function createSession(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    setCreatingSession(true);
    setError(null);
    const form = event.currentTarget;
    const data = new FormData(form);

    try {
      const response = await fetch(`/api/research-projects/${selected.id}/sessions`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          title: String(data.get("session_title") ?? "").trim(),
          objective: String(data.get("session_objective") ?? "").trim() || null,
          context: { project_title: selected.title },
        }),
      });
      if (!response.ok) {
        setError("The research session could not be created.");
        return;
      }
      const session = (await response.json()) as ResearchSession;
      setSessions((current) => [session, ...current]);
      setActiveSession(session);
      form.reset();
    } catch {
      setError("The research session service is unavailable.");
    } finally {
      setCreatingSession(false);
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
              onClick={() => selectProject(project)}
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
              <Link
                className="primary-link"
                href={`/mentor?research_project=${selected.id}${activeSession ? `&research_session=${activeSession.id}` : ""}`}
              >
                Ask AI Mentor
              </Link>
            </div>

            <div className="research-card-grid">
              <article><span>Status</span><strong>{selected.status}</strong><p>Current project lifecycle state.</p></article>
              <article><span>Sessions</span><strong>{sessions.length}</strong><p>Focused investigations saved to this project.</p></article>
            </div>

            <section className="research-sessions">
              <div className="research-section-heading">
                <div><p className="eyebrow">RESEARCH SESSIONS</p><h3>Continue focused work</h3></div>
              </div>
              <div className="research-session-layout">
                <div className="research-session-list">
                  {sessions.length ? sessions.map((session) => (
                    <button
                      type="button"
                      key={session.id}
                      className={activeSession?.id === session.id ? "active" : ""}
                      onClick={() => setActiveSession(session)}
                    >
                      <strong>{session.title}</strong>
                      <span>{session.objective ?? session.summary ?? "Focused research session"}</span>
                    </button>
                  )) : <p className="muted">Create a session to preserve a focused line of inquiry.</p>}
                </div>
                <article className="research-session-detail">
                  {activeSession ? (
                    <>
                      <span>{activeSession.status}</span>
                      <h4>{activeSession.title}</h4>
                      <p>{activeSession.objective ?? activeSession.summary ?? "No session objective has been recorded."}</p>
                    </>
                  ) : (
                    <><h4>No active session</h4><p>Create one below to organize a focused investigation.</p></>
                  )}
                </article>
              </div>
              <form className="research-session-form" onSubmit={createSession}>
                <label>Session title<input name="session_title" required maxLength={160} /></label>
                <label>Objective<textarea name="session_objective" /></label>
                <button type="submit" disabled={creatingSession}>{creatingSession ? "Creating…" : "Create session"}</button>
              </form>
            </section>

            <ResearchNotebookEditor project={selected} onSaved={updateProject} />
          </section>
        ) : (
          <section className="research-empty"><h2>Create your first research project</h2><p>Start with a clear question, objective, and evidence trail.</p></section>
        )}

        <section className="research-create-panel">
          <div><p className="eyebrow">NEW PROJECT</p><h3>Begin a structured investigation</h3></div>
          <form onSubmit={createProject}>
            <label>Title<input name="title" required maxLength={160} /></label>
            <label>Description<textarea name="description" /></label>
            <label>Objective<textarea name="objective" /></label>
            <button type="submit" disabled={creatingProject}>{creatingProject ? "Creating…" : "Create project"}</button>
          </form>
          {error ? <p role="alert" className="form-message">{error}</p> : null}
        </section>
      </main>
    </div>
  );
}
