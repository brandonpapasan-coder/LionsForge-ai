"use client";

import { FormEvent, useEffect, useState } from "react";

type Synthesis = { findings: string | null; limitations: string | null; unresolved_questions: string | null; authorship: "user_authored" };
type Report = { contract_version: string; claims: Array<{ id: number; statement: string; relationship_counts: Record<string, number>; latest_judgment: { validation_status: string; confidence_level: string; rationale: string; authorship: "user_judgment" } | null }>; aggregate_relationship_counts: Record<string, number>; limitations: string[]; unresolved_questions: string[]; interpretation_notice: string };

export function InvestigationSynthesisPanel({ investigationId }: { investigationId: number }) {
  const [findings, setFindings] = useState("");
  const [limitations, setLimitations] = useState("");
  const [questions, setQuestions] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [synthesisResponse, reportResponse] = await Promise.all([
        fetch(`/api/investigations/${investigationId}/synthesis`, { cache: "no-store" }),
        fetch(`/api/investigations/${investigationId}/validation-report`, { cache: "no-store" }),
      ]);
      if (synthesisResponse.status === 401 || reportResponse.status === 401) { window.location.href = "/login"; return; }
      if (synthesisResponse.ok) {
        const synthesis = (await synthesisResponse.json()) as Synthesis;
        setFindings(synthesis.findings ?? ""); setLimitations(synthesis.limitations ?? ""); setQuestions(synthesis.unresolved_questions ?? "");
      } else if (synthesisResponse.status !== 404) throw new Error();
      if (!reportResponse.ok) throw new Error();
      setReport((await reportResponse.json()) as Report);
    } catch { setError("Synthesis and validation report are temporarily unavailable."); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, [investigationId]);

  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError(null);
    try {
      const response = await fetch(`/api/investigations/${investigationId}/synthesis`, {
        method: "PUT", headers: { "content-type": "application/json" },
        body: JSON.stringify({ findings, limitations, unresolved_questions: questions }),
      });
      if (response.status === 422) { setError("Add at least one finding, limitation, or unresolved question."); return; }
      if (!response.ok) throw new Error();
      await load();
    } catch { setError("The synthesis could not be saved."); }
    finally { setSaving(false); }
  }

  return <section className="lesson-card" aria-label="Investigation synthesis and validation report">
    <h4>Synthesis and report</h4>
    <p>Your synthesis and all validation judgments are human-authored interpretations, not automated truth.</p>
    {loading ? <p>Loading synthesis and report…</p> : null}
    {!loading ? <form onSubmit={save}>
      <label>Findings<textarea value={findings} maxLength={20000} onChange={(event) => setFindings(event.target.value)} /></label>
      <label>Limitations<textarea value={limitations} maxLength={12000} onChange={(event) => setLimitations(event.target.value)} /></label>
      <label>Unresolved questions<textarea value={questions} maxLength={12000} onChange={(event) => setQuestions(event.target.value)} /></label>
      <button type="submit" disabled={saving}>{saving ? "Saving…" : "Save synthesis"}</button>
    </form> : null}
    {report ? <div aria-label="Validation report preview">
      <div className="lesson-meta"><span>contract {report.contract_version}</span><span>{report.claims.length} claims</span></div>
      {report.claims.length === 0 ? <p>No claims are available for this report yet.</p> : report.claims.map((claim) => <article key={claim.id} className="lesson-card">
        <h5>{claim.statement}</h5>
        <p>Supports: {claim.relationship_counts.supports ?? 0} · Contradicts: {claim.relationship_counts.contradicts ?? 0} · Neutral: {claim.relationship_counts.neutral ?? 0}</p>
        {claim.latest_judgment ? <p><strong>User judgment:</strong> {claim.latest_judgment.validation_status} ({claim.latest_judgment.confidence_level}) — {claim.latest_judgment.rationale}</p> : <p>No validation judgment recorded.</p>}
      </article>)}
      <p>{report.interpretation_notice}</p>
    </div> : !loading && !error ? <p>Report preview is unavailable.</p> : null}
    {error ? <p role="alert">{error}</p> : null}
  </section>;
}
