"use client";

import { useEffect, useMemo, useState } from "react";

import {
  competencyGapPlanClient,
  type CompetencyGapStatus,
  type LearnerCompetencyGapPlanBundle,
} from "@/lib/competency-gap-plan";

const STATUS_LABELS: Record<CompetencyGapStatus, string> = {
  demonstrated: "Demonstrated",
  developing: "Developing",
  not_yet_demonstrated: "Not yet demonstrated",
};

const REASON_LABELS = {
  adds_not_yet_demonstrated_competency: "Adds a competency not yet demonstrated",
  strengthens_developing_competency: "Strengthens a developing competency",
};

function downloadPlan(bundle: LearnerCompetencyGapPlanBundle) {
  const blob = new Blob([`${JSON.stringify(bundle, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `learner-competency-gap-plan-${bundle.plan.learner_user_id}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function LearnerCompetencyGapPlan() {
  const [bundle, setBundle] = useState<LearnerCompetencyGapPlanBundle | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | CompetencyGapStatus>("all");
  const [competencyFilter, setCompetencyFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    competencyGapPlanClient
      .load()
      .then((value) => { if (active) setBundle(value); })
      .catch((requestError) => {
        if (active) setError(requestError instanceof Error ? requestError.message : "The competency roadmap could not be loaded.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const filteredCompetencies = useMemo(() => {
    const query = competencyFilter.trim().toLowerCase();
    return (bundle?.plan.competencies ?? []).filter((item) => {
      const statusMatches = statusFilter === "all" || item.status === statusFilter;
      const competencyMatches = !query || item.competency_key.toLowerCase().includes(query) || item.competency_label.toLowerCase().includes(query);
      return statusMatches && competencyMatches;
    });
  }, [bundle, competencyFilter, statusFilter]);

  const visibleRecommendations = useMemo(() => {
    const visibleKeys = new Set(filteredCompetencies.map((item) => item.competency_key));
    if (!competencyFilter.trim() && statusFilter === "all") return bundle?.plan.recommendations ?? [];
    return (bundle?.plan.recommendations ?? []).filter((item) => item.competency_keys.some((key) => visibleKeys.has(key)));
  }, [bundle, competencyFilter, filteredCompetencies, statusFilter]);

  return (
    <section className="lesson-card" aria-labelledby="competency-gap-plan-heading">
      <div className="lesson-meta"><span>deterministic learning guidance</span><span>{visibleRecommendations.length} next-practice options</span></div>
      <h2 id="competency-gap-plan-heading">Competency development roadmap</h2>
      <p>
        Review demonstrated, developing, and not-yet-demonstrated competencies, then inspect bounded next-practice recommendations generated from your verified portfolio and active practicum catalog.
      </p>
      <p>
        Recommendations are educational guidance, not accreditation, licensing, degree equivalence, professional certification, employment qualification, individualized financial advice, or autonomous competency approval.
      </p>

      <div className="practicum-form-grid" aria-label="Filter competency roadmap">
        <label>
          Competency status
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as "all" | CompetencyGapStatus)}>
            <option value="all">All statuses</option>
            <option value="demonstrated">Demonstrated</option>
            <option value="developing">Developing</option>
            <option value="not_yet_demonstrated">Not yet demonstrated</option>
          </select>
        </label>
        <label>
          Competency
          <input value={competencyFilter} onChange={(event) => setCompetencyFilter(event.target.value)} placeholder="evidence validation" />
        </label>
        <button type="button" disabled={statusFilter === "all" && !competencyFilter} onClick={() => { setStatusFilter("all"); setCompetencyFilter(""); }}>Clear filters</button>
      </div>

      <p role="status" aria-live="polite">
        {loading ? "Loading competency roadmap…" : bundle ? `${filteredCompetencies.length} competencies and ${visibleRecommendations.length} recommendations match the current filters.` : "Competency roadmap unavailable."}
      </p>
      {error ? <p role="alert">{error}</p> : null}

      {bundle ? (
        <>
          <div className="lesson-meta"><span>Plan digest</span><code>{bundle.receipt.plan_sha256}</code></div>
          <div className="lesson-meta"><span>Source portfolio digest</span><code>{bundle.plan.portfolio_sha256}</code></div>
          <p>Demonstrated status requires {bundle.plan.thresholds.demonstrated_minimum_completed_practica} completed, human-approved supporting practica.</p>
          <button type="button" onClick={() => downloadPlan(bundle)}>Export deterministic JSON</button>
          <p>
            The export contains competency status, template and objective identifiers, prerequisite lesson slugs, estimated effort, deterministic reason codes, and integrity digests. It excludes research content, reflections, prompts, reviewer notes, credentials, answer material, private user content, and hidden assessment metadata.
          </p>
          {bundle.source_portfolio_excluded_record_count > 0 ? <p role="status">The source portfolio excluded {bundle.source_portfolio_excluded_record_count} record(s) that failed integrity requirements.</p> : null}

          <h3>Competency status</h3>
          {filteredCompetencies.length === 0 ? <p>No competencies match the current filters.</p> : filteredCompetencies.map((item) => (
            <article key={item.competency_key} aria-label={`${item.competency_label} competency status`}>
              <h4>{item.competency_label}</h4>
              <p><strong>{STATUS_LABELS[item.status]}</strong> · {item.supporting_completed_practicum_count} supporting completed practicum record(s)</p>
              <p>Competency key: <code>{item.competency_key}</code></p>
            </article>
          ))}

          <h3>Recommended next practica</h3>
          {visibleRecommendations.length === 0 ? <p>No active practica are recommended for the current roadmap filters.</p> : visibleRecommendations.map((item) => (
            <article key={`${item.template_slug}:${item.template_version}`} aria-label={`Recommended practicum ${item.template_slug}`}>
              <h4>{item.template_slug} · version {item.template_version}</h4>
              <p>{item.estimated_minutes} estimated minutes · competencies: {item.competency_keys.join(", ")}</p>
              <p>Objectives: {item.objective_keys.join(", ")}</p>
              <p>Reason: {item.reason_codes.map((code) => REASON_LABELS[code]).join("; ")}</p>
              <p>Prerequisites: {item.prerequisite_lesson_slugs.length ? item.prerequisite_lesson_slugs.join(", ") : "None listed"}</p>
            </article>
          ))}
        </>
      ) : null}
    </section>
  );
}
