"use client";

import { useEffect, useState } from "react";

type Checkpoint = { key: string; label: string; state: "complete" | "remaining" | "blocked"; external: boolean; issue_number: number | null };
type Phase = { key: string; label: string; weight: number; completed_points: number; completion_percent: number; state: "complete" | "remaining" | "blocked"; checkpoints: Checkpoint[] };
type Countdown = {
  overall_completion_percent: number;
  completed_points: number;
  remaining_points: number;
  total_points: number;
  completed_checkpoints: number;
  remaining_checkpoints: number;
  blocked_checkpoints: number;
  external_checkpoints: number;
  remaining_milestones: number;
  current_blocker: string | null;
  next_action: string | null;
  phases: Phase[];
  disclaimer: string;
};

export function ReleaseCountdownPanel() {
  const [data, setData] = useState<Countdown | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void fetch("/api/release-countdown", { cache: "no-store", signal: controller.signal })
      .then(async (response) => {
        if (response.status === 401) {
          window.location.href = "/login";
          return null;
        }
        if (!response.ok) throw new Error("Release countdown could not be loaded.");
        return (await response.json()) as Countdown;
      })
      .then((payload) => { if (payload) setData(payload); })
      .catch((requestError) => {
        if (requestError instanceof DOMException && requestError.name === "AbortError") return;
        setError(requestError instanceof Error ? requestError.message : "Release countdown could not be loaded.");
      });
    return () => controller.abort();
  }, []);

  return (
    <section className="dashboard-panel" aria-labelledby="release-countdown-title">
      <div className="panel-heading"><div><p className="eyebrow">FULL DEVELOPMENT COUNTDOWN</p><h2 id="release-countdown-title">Release completion</h2></div></div>
      {error ? <p role="alert">{error}</p> : !data ? <p className="muted">Loading verified release progress…</p> : (
        <>
          <div className="metric-grid" aria-label="Release countdown metrics">
            <article className="metric-card"><span>Overall completion</span><strong>{data.overall_completion_percent}%</strong><p>{data.completed_points}/{data.total_points} verified points</p></article>
            <article className="metric-card"><span>Remaining points</span><strong>{data.remaining_points}</strong><p>{data.remaining_checkpoints} checkpoints</p></article>
            <article className="metric-card"><span>Blocking milestones</span><strong>{data.remaining_milestones}</strong><p>{data.blocked_checkpoints} blocked checkpoint</p></article>
            <article className="metric-card"><span>External checkpoints</span><strong>{data.external_checkpoints}</strong><p>Require staging evidence</p></article>
          </div>
          {data.current_blocker ? <p><strong>Current blocker:</strong> {data.current_blocker}</p> : null}
          {data.next_action ? <p><strong>Next release action:</strong> {data.next_action}</p> : null}
          <div className="action-list" aria-label="Release countdown phases">
            {data.phases.map((phase) => (
              <article className="action-card" key={phase.key}>
                <div>
                  <span className={`priority priority-${phase.state === "complete" ? "low" : phase.state === "blocked" ? "high" : "medium"}`}>{phase.state}</span>
                  <h3>{phase.label}</h3>
                  <p>{phase.completion_percent}% complete · {phase.completed_points}/{phase.weight} points</p>
                  <ul>{phase.checkpoints.map((checkpoint) => <li key={checkpoint.key}><strong>{checkpoint.state.replaceAll("_", " ")}:</strong> {checkpoint.label}{checkpoint.issue_number ? ` · Issue #${checkpoint.issue_number}` : ""}</li>)}</ul>
                </div>
              </article>
            ))}
          </div>
          <p className="muted">{data.disclaimer}</p>
        </>
      )}
    </section>
  );
}
