"use client";

import { useCallback, useEffect, useState } from "react";

import type { EvidenceGapRemediationPlan } from "@/lib/investigations";

export function EvidenceGapRemediationPanel({ investigationId }: { investigationId: number }) {
  const [plan, setPlan] = useState<EvidenceGapRemediationPlan | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const retry = useCallback(() => {
    setPlan(null);
    setUnavailable(false);
    setReloadToken((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch(`/api/investigations/${investigationId}/remediation-plan`, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (response.status === 401) {
          window.location.href = "/login";
          return;
        }
        if (!response.ok) {
          setUnavailable(true);
          return;
        }
        const payload = (await response.json()) as EvidenceGapRemediationPlan;
        if (!controller.signal.aborted) setPlan(payload);
      } catch {
        if (!controller.signal.aborted) setUnavailable(true);
      }
    }
    void load();
    return () => controller.abort();
  }, [investigationId, reloadToken]);

  return (
    <section aria-label="Evidence gap remediation plan">
      <h4>Evidence-gap remediation plan</h4>
      <p>These next actions are derived only from recorded gaps and review state. They do not invent sources, deadlines, confidence, conclusions, or research completion.</p>
      {plan === null && !unavailable ? <p role="status">Building the remediation plan from recorded evidence gaps…</p> : null}
      {unavailable ? (
        <div role="status">
          <p>The remediation plan is temporarily unavailable.</p>
          <button type="button" onClick={retry}>Retry remediation plan</button>
        </div>
      ) : null}
      {plan?.status === "empty" ? <p>No material claims are recorded, so no remediation actions can be derived.</p> : null}
      {plan?.status === "complete" ? <p role="status">No recorded evidence gap or stale review currently requires remediation.</p> : null}
      {plan?.actions.map((action) => (
        <article key={action.claim_id} className="lesson-card" aria-label={`${action.statement}: priority ${action.priority}`}>
          <div className="lesson-meta"><span>Priority {action.priority}</span><span>{action.action_type.replaceAll("_", " ")}</span></div>
          <h5>{action.statement}</h5>
          <p><strong>Claim state:</strong> {action.claim_status}</p>
          <p><strong>Why this priority:</strong> {action.priority_rule}</p>
          <p><strong>Required action:</strong> {action.rationale}</p>
          <p><strong>Human review refresh:</strong> {action.review_refresh_required ? "required" : "not currently required"}</p>
          {action.source_requirements.length > 0 ? (
            <div>
              <strong>Evidence requirements</strong>
              {action.source_requirements.map((item) => (
                <div key={item.requirement}>
                  <p>{item.requirement}</p>
                  <ul aria-label={`Source constraints for ${item.requirement}`}>
                    {item.source_constraints.map((constraint) => <li key={constraint}>{constraint}</li>)}
                  </ul>
                </div>
              ))}
            </div>
          ) : <p>No new source requirement is recorded; refresh the human review against current stored evidence.</p>}
          <div><strong>Completion criteria</strong><ul>{action.completion_criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}</ul></div>
          <details><summary>Show deterministic inputs</summary><ul>{action.stored_inputs.map((input) => <li key={input}><code>{input}</code></li>)}</ul></details>
        </article>
      ))}
    </section>
  );
}