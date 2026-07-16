"use client";

import { useEffect, useState } from "react";

import type { MarketLearningProgress } from "@/lib/market-learning-progress";

const SCENARIOS = [
  "bull_market",
  "bear_market",
  "high_volatility",
  "inflation_shock",
  "rate_cut_rally",
] as const;

const isAbortError = (error: unknown) => error instanceof DOMException && error.name === "AbortError";
const label = (value: string) => value.replaceAll("_", " ");
const percent = (value: string) => `${(Number(value) * 100).toFixed(1)}%`;

export function MarketLearningProgressPanel() {
  const [data, setData] = useState<MarketLearningProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        const response = await fetch("/api/market-simulator/learning-progress", {
          cache: "no-store",
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) {
          setError("Market learning progress could not be loaded.");
          return;
        }
        setData((await response.json()) as MarketLearningProgress);
      } catch (requestError) {
        if (!isAbortError(requestError) && !controller.signal.aborted) {
          setError("The market learning service is unavailable.");
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void load();
    return () => controller.abort();
  }, []);

  if (loading) {
    return <section className="dashboard-state" aria-live="polite">Loading market learning progress…</section>;
  }
  if (error) {
    return <section className="dashboard-state" role="alert">{error}</section>;
  }
  if (!data) return null;

  const empty = data.completed_sessions === 0;

  return (
    <section className="dashboard-panel" aria-labelledby="market-learning-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">MARKET SIMULATOR LEARNING</p>
          <h2 id="market-learning-title">Educational progress</h2>
          <p className="muted">Simulation-based learning only · {data.disclaimer}</p>
        </div>
      </div>

      {empty ? (
        <div className="dashboard-state">
          <strong>No completed learning sessions yet.</strong>
          <p>Complete a guided market scenario and reflection to begin building evidence of learning.</p>
        </div>
      ) : (
        <>
          <div className="metric-grid" aria-label="Market learning metrics">
            <article className="metric-card"><span>Learning level</span><strong>{label(data.proficiency_level)}</strong><p>{data.completed_sessions} completed sessions</p></article>
            <article className="metric-card"><span>Scenario coverage</span><strong>{data.unique_scenarios}/5</strong><p>Deterministic scenarios explored</p></article>
            <article className="metric-card"><span>Average simulated return</span><strong>{percent(data.average_projected_return)}</strong><p>Educational scenario outcome, not investment performance</p></article>
            <article className="metric-card"><span>Evidence badge</span><strong>{data.evidence_badge_eligible ? "Eligible" : "In progress"}</strong><p>Based on learning-session breadth and completion</p></article>
          </div>

          <div className="dashboard-grid">
            <section>
              <div className="panel-heading"><div><p className="eyebrow">SCENARIO COVERAGE</p><h3>Practice across market conditions</h3></div></div>
              <div className="activity-list">
                {SCENARIOS.map((scenario) => (
                  <div className="activity-card" key={scenario}>
                    <span>{data.scenario_counts[scenario] ?? 0}</span>
                    <div><strong>{label(scenario)}</strong><p>Completed learning sessions</p></div>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <div className="panel-heading"><div><p className="eyebrow">NEXT LEARNING STEP</p><h3>Continue deliberately</h3></div></div>
              <div className="activity-list">
                <div className="activity-card"><span>Next</span><div><strong>{data.next_learning_step}</strong></div></div>
                {Object.entries(data.risk_tier_counts).map(([tier, count]) => (
                  <div className="activity-card" key={tier}><span>{count}</span><div><strong>{label(tier)} risk reflections</strong></div></div>
                ))}
              </div>
            </section>
          </div>
        </>
      )}
    </section>
  );
}
