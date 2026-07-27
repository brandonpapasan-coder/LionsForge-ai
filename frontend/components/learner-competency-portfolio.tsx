"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  type LearnerCompetencyPortfolioBundle,
  researchPracticumClient,
} from "@/lib/research-practicum";

function downloadPortfolio(bundle: LearnerCompetencyPortfolioBundle) {
  const blob = new Blob([`${JSON.stringify(bundle, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `learner-competency-portfolio-${bundle.portfolio.learner_user_id}.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function LearnerCompetencyPortfolio() {
  const [bundle, setBundle] = useState<LearnerCompetencyPortfolioBundle | null>(null);
  const [competencyKey, setCompetencyKey] = useState("");
  const [templateSlug, setTemplateSlug] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (filters: { competency_key?: string; template_slug?: string } = {}) => {
    setLoading(true);
    setError(null);
    try {
      setBundle(await researchPracticumClient.competencyPortfolio(filters));
    } catch (requestError) {
      setBundle(null);
      setError(requestError instanceof Error ? requestError.message : "The competency portfolio could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const totals = useMemo(() => {
    const competencies = bundle?.portfolio.competencies ?? [];
    return {
      competencies: competencies.length,
      practica: competencies.reduce((sum, item) => sum + item.completed_practicum_count, 0),
      objectives: competencies.reduce((sum, item) => sum + item.practica.reduce((count, practicum) => count + practicum.objective_keys.length, 0), 0),
      evidenceReferences: competencies.reduce((sum, item) => sum + item.practica.reduce((count, practicum) => count + practicum.referenced_evidence_ids.length, 0), 0),
    };
  }, [bundle]);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void load({ competency_key: competencyKey || undefined, template_slug: templateSlug || undefined });
  }

  return (
    <section className="lesson-card" aria-labelledby="competency-portfolio-heading">
      <div className="lesson-meta"><span>evidence-backed learning</span><span>{totals.competencies} competencies</span></div>
      <h2 id="competency-portfolio-heading">Learner competency portfolio</h2>
      <p>
        Review competencies demonstrated through completed, human-approved research practica and inspect the underlying audit provenance.
        This portfolio is not accreditation, licensing, degree equivalence, professional certification, employment verification, or autonomous competency approval.
      </p>

      <form className="practicum-form-grid" onSubmit={applyFilters} aria-label="Filter competency portfolio">
        <label>
          Competency key
          <input value={competencyKey} onChange={(event) => setCompetencyKey(event.target.value)} placeholder="evidence_validation" />
        </label>
        <label>
          Template slug
          <input value={templateSlug} onChange={(event) => setTemplateSlug(event.target.value)} placeholder="research-evidence-practicum" />
        </label>
        <button disabled={loading} type="submit">Apply filters</button>
        <button disabled={loading || (!competencyKey && !templateSlug)} type="button" onClick={() => { setCompetencyKey(""); setTemplateSlug(""); void load(); }}>Clear filters</button>
      </form>

      <p role="status" aria-live="polite">
        {loading
          ? "Loading competency portfolio…"
          : bundle
            ? `${totals.competencies} competencies, ${totals.practica} supporting practica, ${totals.objectives} objectives, and ${totals.evidenceReferences} evidence references.`
            : "Competency portfolio unavailable."}
      </p>
      {error ? <p role="alert">{error}</p> : null}

      {bundle ? (
        <>
          <div className="lesson-meta">
            <span>Portfolio digest</span>
            <code>{bundle.receipt.portfolio_sha256}</code>
          </div>
          <button type="button" onClick={() => downloadPortfolio(bundle)}>Export deterministic JSON</button>
          <p>
            The export contains stable identifiers, completion dates, objective keys, evidence-reference IDs, final human decision IDs, and audit digests.
            It excludes research content, learner reflections, prompts, reviewer notes, credentials, answer material, and private user content.
          </p>
          {bundle.portfolio.excluded_record_count > 0 ? (
            <p role="status">{bundle.portfolio.excluded_record_count} completed record(s) were excluded because they did not satisfy portfolio integrity requirements.</p>
          ) : null}

          {bundle.portfolio.competencies.length === 0 ? (
            <p>No completed, human-approved practica match the current portfolio filters.</p>
          ) : bundle.portfolio.competencies.map((competency) => (
            <article key={competency.competency_key} aria-labelledby={`competency-${competency.competency_key}`}>
              <h3 id={`competency-${competency.competency_key}`}>{competency.competency_label}</h3>
              <p>{competency.completed_practicum_count} supporting completed practicum record(s).</p>
              {competency.practica.map((practicum) => (
                <section key={`${competency.competency_key}:${practicum.enrollment_id}`} aria-label={`Practicum ${practicum.enrollment_id}`}>
                  <p><strong>{practicum.template_slug}</strong> · version {practicum.template_version} · completed {new Date(practicum.completed_at).toLocaleDateString("en-US")}</p>
                  <p>Enrollment {practicum.enrollment_id} · Project {practicum.research_project_id} · Final human decision {practicum.final_review_decision_id}</p>
                  <p>Objectives: {practicum.objective_keys.join(", ")}</p>
                  <p>Evidence references: {practicum.referenced_evidence_ids.length}</p>
                  <p>Completion audit digest: <code>{practicum.completion_record_sha256}</code></p>
                </section>
              ))}
            </article>
          ))}
        </>
      ) : null}
    </section>
  );
}
