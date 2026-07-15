"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import type { ResearchProject } from "@/lib/research";

type NotebookContext = {
  thesis?: string;
  evidence?: string;
  risks?: string;
  decision_journal?: string;
};

type ResearchNotebookEditorProps = {
  project: ResearchProject;
  onSaved: (project: ResearchProject) => void;
};

export function ResearchNotebookEditor({ project, onSaved }: ResearchNotebookEditorProps) {
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const saveRequest = useRef<AbortController | null>(null);
  const notebook = (project.context?.notebook ?? {}) as NotebookContext;

  useEffect(() => {
    saveRequest.current?.abort();
    saveRequest.current = null;
    setSaving(false);
    setMessage(null);

    return () => {
      saveRequest.current?.abort();
      saveRequest.current = null;
    };
  }, [project.id]);

  async function saveNotebook(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    saveRequest.current?.abort();
    const controller = new AbortController();
    saveRequest.current = controller;
    const projectId = project.id;
    const projectContext = project.context;

    setSaving(true);
    setMessage(null);
    const form = new FormData(event.currentTarget);

    try {
      const response = await fetch(`/api/research-projects/${projectId}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          context: {
            ...projectContext,
            notebook: {
              thesis: String(form.get("thesis") ?? "").trim(),
              evidence: String(form.get("evidence") ?? "").trim(),
              risks: String(form.get("risks") ?? "").trim(),
              decision_journal: String(form.get("decision_journal") ?? "").trim(),
            },
          },
        }),
      });
      if (controller.signal.aborted || saveRequest.current !== controller) return;
      if (!response.ok) {
        setMessage("The notebook could not be saved.");
        return;
      }
      const savedProject = (await response.json()) as ResearchProject;
      if (controller.signal.aborted || saveRequest.current !== controller) return;
      onSaved(savedProject);
      setMessage("Notebook saved.");
    } catch (requestError) {
      if (requestError instanceof DOMException && requestError.name === "AbortError") return;
      if (!controller.signal.aborted && saveRequest.current === controller) {
        setMessage("The notebook service is unavailable.");
      }
    } finally {
      if (saveRequest.current === controller) {
        saveRequest.current = null;
        setSaving(false);
      }
    }
  }

  return (
    <section className="research-notebook">
      <div>
        <p className="eyebrow">RESEARCH NOTEBOOK</p>
        <h3>Structure the investigation</h3>
      </div>
      <form className="research-notebook-form" onSubmit={saveNotebook} key={project.id}>
        <label>
          Thesis
          <textarea name="thesis" defaultValue={notebook.thesis ?? ""} placeholder="State the current working conclusion." />
        </label>
        <label>
          Evidence
          <textarea name="evidence" defaultValue={notebook.evidence ?? ""} placeholder="Record supporting and contradicting evidence." />
        </label>
        <label>
          Risks
          <textarea name="risks" defaultValue={notebook.risks ?? ""} placeholder="Record assumptions, uncertainty, and failure conditions." />
        </label>
        <label>
          Decision journal
          <textarea name="decision_journal" defaultValue={notebook.decision_journal ?? ""} placeholder="Track decisions, confidence changes, and reasons." />
        </label>
        <div className="research-notebook-actions">
          <button type="submit" disabled={saving}>{saving ? "Saving…" : "Save notebook"}</button>
          {message ? <span role="status">{message}</span> : null}
        </div>
      </form>
    </section>
  );
}
