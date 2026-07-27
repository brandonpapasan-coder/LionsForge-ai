"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import type { ResearchProject } from "@/lib/research";
import {
  competencyGapPlanClient,
  type CompetencyGapRecommendation,
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
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [statusFilter, setStatusFilter] = useState<"all" | CompetencyGapStatus>("all");
  const [competencyFilter, setCompetencyFilter] = useState("");
  const [selectedRecommendation, setSelectedRecommendation] = useState<CompetencyGapRecommendation | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      competencyGapPlanClient.load(),
      fetch("/api/research-projects", { cache: "no-store" }).then(async (response) => {
        if (response.status === 401) {
          window.location.href = "/login";
          return [] as ResearchProject[];
        }
        if (!response.ok) throw new Error("Research projects could not be loaded.");
        return (await response.json()) as ResearchProject[];
      }),
    ])
      .then(([planBundle, projectRows]) => {
        if (!active) return;
        setBundle(planBundle);
        setProjects(projectRows);
      })
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

  function beginEnrollment(item: CompetencyGapRecommendation) {
    setSelectedRecommendation(item);
    setSelectedProjectId("");
    setConfirmed(false);
    setActionError(null);
  }

  async function submitEnrollment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedRecommendation || !selectedProjectId || !confirmed) return;
    setSubmitting(true);
    setActionError(null);
    try {
      await competencyGapPlanClient.startRecommendedPracticum(
        selectedRecommendation.template_slug,
        selectedRecommendation.template_version,
        Number(selectedProjectId),
      );
      window.location.reload();
    } catch (requestError) {
      setActionError(requestError instanceof Error ? requestError.message : "The recommended practicum could not be started.");
    } finally {
      setSubmitting(false);
    }
  }

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
              <button type="button" onClick={() => beginEnrollment(item)}>Start recommended practicum</button>
            </article>
          ))}

          {selectedRecommendation ? (
            <form className="practicum-form-grid" onSubmit={submitEnrollment} aria-label="Confirm recommended practicum enrollment">
              <h3>Confirm learner-requested enrollment</h3>
              <p>
                You selected <strong>{selectedRecommendation.template_slug}</strong> version {selectedRecommendation.template_version}. The server will regenerate the current roadmap, confirm this exact recommendation remains active, verify prerequisites and project ownership, and prevent duplicate enrollment.
              </p>
              <p>Recommendation reason: {selectedRecommendation.reason_codes.map((code) => REASON_LABELS[code]).join("; ")}</p>
              <p>Estimated effort: {selectedRecommendation.estimated_minutes} minutes. Prerequisites: {selectedRecommendation.prerequisite_lesson_slugs.length ? selectedRecommendation.prerequisite_lesson_slugs.join(", ") : "None listed"}.</p>
              <label>
                Research project
                <select required value={selectedProjectId} onChange={(event) => setSelectedProjectId(event.target.value)}>
                  <option value="">Select one of your research projects</option>
                  {projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}
                </select>
              </label>
              {projects.length === 0 ? <p role="status">Create a research project before starting a recommended practicum.</p> : null}
              <label>
                <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
                I explicitly request this enrollment and understand the roadmap is educational guidance, not a credential or autonomous competency decision.
              </label>
              <button type="submit" disabled={submitting || !selectedProjectId || !confirmed}>{submitting ? "Starting practicum…" : "Confirm and start practicum"}</button>
              <button type="button" disabled={submitting} onClick={() => setSelectedRecommendation(null)}>Cancel</button>
              <p role="status" aria-live="polite">{submitting ? "Revalidating the current recommendation and enrollment requirements…" : "No enrollment occurs until you explicitly submit this form."}</p>
              {actionError ? <p role="alert">{actionError}</p> : null}
            </form>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
