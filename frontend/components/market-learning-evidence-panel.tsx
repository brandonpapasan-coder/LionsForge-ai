"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import type {
  MarketLearningEvidenceHistory,
  MarketLearningSession,
  ResearchProjectSummary,
} from "@/lib/market-learning-evidence";

const isAbortError = (error: unknown) => error instanceof DOMException && error.name === "AbortError";
const label = (value: string) => value.replaceAll("_", " ");
const percent = (value: string) => `${(Number(value) * 100).toFixed(1)}%`;

export function MarketLearningEvidencePanel() {
  const [sessions, setSessions] = useState<MarketLearningSession[]>([]);
  const [projects, setProjects] = useState<ResearchProjectSummary[]>([]);
  const [historyBySession, setHistoryBySession] = useState<Record<number, MarketLearningEvidenceHistory>>({});
  const [selectedSessionId, setSelectedSessionId] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [claim, setClaim] = useState("");
  const [contradictionKey, setContradictionKey] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        const [sessionsResponse, projectsResponse] = await Promise.all([
          fetch("/api/market-simulator/learning-sessions", { cache: "no-store", signal: controller.signal }),
          fetch("/api/research-projects", { cache: "no-store", signal: controller.signal }),
        ]);
        if (controller.signal.aborted) return;
        if (sessionsResponse.status === 401 || projectsResponse.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!sessionsResponse.ok || !projectsResponse.ok) {
          setError("Market learning evidence data could not be loaded.");
          return;
        }

        const loadedSessions = (await sessionsResponse.json()) as MarketLearningSession[];
        const loadedProjects = (await projectsResponse.json()) as ResearchProjectSummary[];
        const histories = await Promise.all(
          loadedSessions.map(async (session) => {
            const response = await fetch(`/api/market-simulator/learning-evidence/${session.id}`, {
              cache: "no-store",
              signal: controller.signal,
            });
            if (response.status === 404) return null;
            if (response.status === 401) {
              window.location.href = "/login";
              return null;
            }
            if (!response.ok) throw new Error("Evidence history unavailable");
            return (await response.json()) as MarketLearningEvidenceHistory;
          }),
        );
        if (controller.signal.aborted) return;

        setSessions(loadedSessions);
        setProjects(loadedProjects.filter((project) => project.status === "active"));
        setHistoryBySession(
          histories.reduce<Record<number, MarketLearningEvidenceHistory>>((items, history) => {
            if (history) items[history.evidence.session_id] = history;
            return items;
          }, {}),
        );
      } catch (requestError) {
        if (!isAbortError(requestError) && !controller.signal.aborted) {
          setError("The market learning evidence service is unavailable.");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void load();
    return () => controller.abort();
  }, []);

  const eligibleSessions = useMemo(
    () => sessions.filter((session) => session.status === "completed" && !historyBySession[session.id]),
    [historyBySession, sessions],
  );
  const reviewedSessions = useMemo(
    () => sessions.filter((session) => historyBySession[session.id]),
    [historyBySession, sessions],
  );

  async function submitEvidence(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setSubmitting(true);
    try {
      const response = await fetch("/api/market-simulator/learning-evidence", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          session_id: Number(selectedSessionId),
          project_id: Number(selectedProjectId),
          claim: claim.trim(),
          stance: "supports",
          contradiction_key: contradictionKey.trim() || null,
        }),
      });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (response.status === 409) {
        setError("This learning session has already been submitted as evidence.");
        return;
      }
      if (!response.ok) {
        setError("The learning evidence could not be submitted. Review the selected session, project, and claim.");
        return;
      }

      const created = (await response.json()) as MarketLearningEvidenceHistory["evidence"];
      setHistoryBySession((current) => ({
        ...current,
        [created.session_id]: { evidence: created, reviews: [] },
      }));
      setSelectedSessionId("");
      setSelectedProjectId("");
      setClaim("");
      setContradictionKey("");
      setNotice("Simulated educational evidence submitted for review.");
    } catch {
      setError("The learning evidence service is unavailable.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <section className="dashboard-state" aria-live="polite">Loading learning evidence workflow…</section>;
  }
  if (error && sessions.length === 0) {
    return <section className="dashboard-state" role="alert">{error}</section>;
  }

  return (
    <section className="dashboard-panel" aria-labelledby="market-evidence-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">SIMULATED LEARNING EVIDENCE</p>
          <h2 id="market-evidence-title">Submit and review learning claims</h2>
          <p className="muted">Educational simulation only. Approval does not establish investment success, predictive accuracy, or real-world empirical validation.</p>
        </div>
      </div>

      {notice ? <p className="dashboard-state" role="status">{notice}</p> : null}
      {error ? <p className="dashboard-state" role="alert">{error}</p> : null}

      <div className="dashboard-grid">
        <section>
          <div className="panel-heading"><div><p className="eyebrow">SUBMISSION</p><h3>Convert a completed session</h3></div></div>
          {eligibleSessions.length === 0 ? (
            <div className="dashboard-state">
              <strong>No eligible sessions.</strong>
              <p>Complete another guided scenario, or review previously submitted learning evidence below.</p>
            </div>
          ) : projects.length === 0 ? (
            <div className="dashboard-state">
              <strong>No active research project.</strong>
              <p>Create an active research project before submitting simulated educational evidence.</p>
            </div>
          ) : (
            <form className="activity-list" onSubmit={submitEvidence}>
              <label className="activity-card">
                <span>1</span>
                <div>
                  <strong>Learning session</strong>
                  <select aria-label="Learning session" required value={selectedSessionId} onChange={(event) => setSelectedSessionId(event.target.value)}>
                    <option value="">Select a completed session</option>
                    {eligibleSessions.map((session) => (
                      <option value={session.id} key={session.id}>
                        {label(session.scenario_name)} · {label(session.risk_tier)} risk · {percent(session.projected_return)} simulated
                      </option>
                    ))}
                  </select>
                </div>
              </label>
              <label className="activity-card">
                <span>2</span>
                <div>
                  <strong>Research project</strong>
                  <select aria-label="Research project" required value={selectedProjectId} onChange={(event) => setSelectedProjectId(event.target.value)}>
                    <option value="">Select an active project</option>
                    {projects.map((project) => <option value={project.id} key={project.id}>{project.title}</option>)}
                  </select>
                </div>
              </label>
              <label className="activity-card">
                <span>3</span>
                <div>
                  <strong>Learner claim</strong>
                  <textarea aria-label="Learner claim" required minLength={20} maxLength={1000} value={claim} onChange={(event) => setClaim(event.target.value)} placeholder="Describe what the simulation demonstrated about risk, diversification, or scenario behavior." />
                </div>
              </label>
              <label className="activity-card">
                <span>4</span>
                <div>
                  <strong>Contradiction key (optional)</strong>
                  <input aria-label="Contradiction key (optional)" maxLength={160} value={contradictionKey} onChange={(event) => setContradictionKey(event.target.value)} placeholder="Example: concentration-downside" />
                </div>
              </label>
              <button className="primary-link" type="submit" disabled={submitting}>{submitting ? "Submitting…" : "Submit simulated evidence"}</button>
            </form>
          )}
        </section>

        <section>
          <div className="panel-heading"><div><p className="eyebrow">REVIEW OUTCOMES</p><h3>Continue the evidence cycle</h3></div></div>
          <div className="activity-list">
            {reviewedSessions.length === 0 ? <p className="muted">Submitted evidence and immutable review history will appear here.</p> : reviewedSessions.map((session) => {
              const history = historyBySession[session.id];
              const evidence = history.evidence;
              return (
                <article className="activity-card" key={session.id}>
                  <span>{label(evidence.evidence.validation_status)}</span>
                  <div>
                    <strong>{label(evidence.scenario_name)} · simulated educational evidence</strong>
                    <p>{evidence.evidence.claim}</p>
                    <p><strong>Reviewer notes:</strong> {evidence.evidence.reviewer_notes ?? "No reviewer notes yet."}</p>
                    <p><strong>Next reflection:</strong> {evidence.next_reflection_prompt}</p>
                    <p>{history.reviews.length} immutable review event{history.reviews.length === 1 ? "" : "s"}</p>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </div>
    </section>
  );
}
