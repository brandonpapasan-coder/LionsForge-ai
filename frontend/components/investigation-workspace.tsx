"use client";

import { FormEvent, useEffect, useState } from "react";

import { ClaimEvidencePanel } from "@/components/claim-evidence-panel";
import { ResearchLearningRecommendations } from "@/components/research-learning-recommendations";
import { ValidationLedgerPanel } from "@/components/validation-ledger-panel";
import type { Investigation, InvestigationStatus } from "@/lib/investigations";

const statuses: InvestigationStatus[] = ["open", "in_review", "validated", "archived"];

export function InvestigationWorkspace() {
  const [items, setItems] = useState<Investigation[] | null>(null);
  const [title, setTitle] = useState("");
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const response = await fetch("/api/investigations", { cache: "no-store" });
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) throw new Error();
        const payload = (await response.json()) as Investigation[];
        if (active) setItems(payload);
      } catch {
        if (active) setError("The Research Validation Workspace is temporarily unavailable.");
      }
    }
    void load();
    return () => { active = false; };
  }, []);

  async function createInvestigation(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/investigations", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ title, research_question: question }),
      });
      if (!response.ok) throw new Error();
      const created = (await response.json()) as Investigation;
      setItems((current) => [created, ...(current ?? [])]);
      setTitle("");
      setQuestion("");
    } catch {
      setError("The investigation could not be created.");
    } finally {
      setBusy(false);
    }
  }

  async function updateStatus(item: Investigation, status: InvestigationStatus) {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/investigations/${item.id}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!response.ok) throw new Error();
      const updated = (await response.json()) as Investigation;
      setItems((current) => [updated, ...(current ?? []).filter((candidate) => candidate.id !== updated.id)]);
    } catch {
      setError("The investigation status could not be updated.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="education-shell">
      <header className="education-hero">
        <div>
          <p className="eyebrow">RESEARCH VALIDATION WORKSPACE</p>
          <h1>Turn questions into auditable investigations.</h1>
          <p>Define the question, map claims to evidence, and preserve a clear validation lifecycle.</p>
        </div>
      </header>

      <section className="lesson-card" aria-label="Create investigation">
        <h2>Start an investigation</h2>
        <form onSubmit={createInvestigation}>
          <label>Title<input value={title} minLength={3} maxLength={160} required onChange={(event) => setTitle(event.target.value)} /></label>
          <label>Research question<textarea value={question} minLength={5} maxLength={4000} required onChange={(event) => setQuestion(event.target.value)} /></label>
          <button type="submit" disabled={busy}>{busy ? "Saving…" : "Create investigation"}</button>
        </form>
      </section>

      <section className="lesson-card" aria-label="Private investigations">
        <div className="lesson-meta"><span>private workspace</span><span>{items?.length ?? 0} investigations</span></div>
        <h2>Your investigations</h2>
        {items === null && !error ? <p>Loading your private investigations…</p> : null}
        {items?.length === 0 ? <p>No investigations yet. Start with a research question above.</p> : null}
        {items && items.length > 0 ? <div className="lesson-grid">{items.map((item) => (
          <article className="lesson-card" key={item.id} data-investigation-status={item.status}>
            <div className="lesson-meta"><span>{item.status.replaceAll("_", " ")}</span><time dateTime={item.updated_at}>{new Date(item.updated_at).toLocaleString()}</time></div>
            <h3>{item.title}</h3><p>{item.research_question}</p>
            <label>Validation status<select value={item.status} disabled={busy} onChange={(event) => void updateStatus(item, event.target.value as InvestigationStatus)}>{statuses.map((status) => <option key={status} value={status}>{status.replaceAll("_", " ")}</option>)}</select></label>
            <ClaimEvidencePanel investigationId={item.id} />
            <ValidationLedgerPanel investigationId={item.id} />
            <ResearchLearningRecommendations investigationId={item.id} />
          </article>
        ))}</div> : null}
        {error ? <p role="alert">{error}</p> : null}
      </section>
    </main>
  );
}
