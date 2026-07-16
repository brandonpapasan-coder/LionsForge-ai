"use client";

import { ChangeEvent, useEffect, useState } from "react";

import { ResearchProvenancePanel } from "@/components/research-provenance-panel";
import type { ResearchProject } from "@/lib/research";

const isAbortError = (error: unknown) => error instanceof DOMException && error.name === "AbortError";
const safeFilename = (title: string, projectId: number) => {
  const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 80) || `project-${projectId}`;
  return `${slug}-evidence-audit-packet.json`;
};
const readFileAsText = (file: File) => new Promise<string>((resolve, reject) => {
  const reader = new FileReader();
  reader.onerror = () => reject(reader.error ?? new Error("File could not be read."));
  reader.onload = () => resolve(typeof reader.result === "string" ? reader.result : "");
  reader.readAsText(file);
});

type VerificationCheck = { code: string; passed: boolean; message: string };
type VerificationResult = { valid: boolean; computed_sha256: string; checks: VerificationCheck[]; disclaimer: string };
type PacketChange = { event_id: string; classification: "added" | "removed" | "changed" | "unchanged"; event_type: string; evidence_id: number; changed_fields: string[]; explanation: string };
type ComparisonResult = {
  comparable: boolean;
  summary: { added: number; removed: number; changed: number; unchanged: number; project_changed: boolean; summary_changed: boolean };
  changes: PacketChange[];
  project_changes: string[];
  summary_changes: string[];
  disclaimer: string;
};

export function ResearchProvenanceSection() {
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [comparing, setComparing] = useState(false);
  const [verification, setVerification] = useState<VerificationResult | null>(null);
  const [baselinePacket, setBaselinePacket] = useState<unknown | null>(null);
  const [currentPacket, setCurrentPacket] = useState<unknown | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch("/api/research-projects", { cache: "no-store", signal: controller.signal });
        if (controller.signal.aborted) return;
        if (response.status === 401) { window.location.href = "/login"; return; }
        if (!response.ok) { setError("Research projects could not be loaded for provenance review."); return; }
        const payload = (await response.json()) as ResearchProject[];
        setProjects(payload);
        setProjectId(payload[0]?.id ?? null);
      } catch (requestError) {
        if (!isAbortError(requestError) && !controller.signal.aborted) setError("The provenance project selector is unavailable.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  async function downloadAuditPacket() {
    if (!projectId) return;
    setDownloading(true); setError(null);
    try {
      const response = await fetch(`/api/research-evidence-audit-packet/${projectId}`, { cache: "no-store" });
      if (response.status === 401) { window.location.href = "/login"; return; }
      if (!response.ok) { setError("The evidence audit packet could not be generated."); return; }
      const packet = await response.json();
      const url = URL.createObjectURL(new Blob([JSON.stringify(packet, null, 2)], { type: "application/json" }));
      const anchor = document.createElement("a");
      const project = projects.find((item) => item.id === projectId);
      anchor.href = url; anchor.download = safeFilename(project?.title ?? `project-${projectId}`, projectId); anchor.click(); URL.revokeObjectURL(url);
    } catch { setError("The evidence audit packet service is unavailable."); } finally { setDownloading(false); }
  }

  async function verifyAuditPacket(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; event.target.value = ""; if (!file) return;
    setVerifying(true); setVerification(null); setError(null);
    try {
      const packet = JSON.parse(await readFileAsText(file)) as unknown;
      const response = await fetch("/api/research-evidence-audit-packet/verify", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(packet) });
      if (response.status === 401) { window.location.href = "/login"; return; }
      if (!response.ok) { setError("The selected audit packet could not be verified."); return; }
      setVerification((await response.json()) as VerificationResult);
    } catch { setError("The selected file is not a valid audit packet JSON document."); } finally { setVerifying(false); }
  }

  async function selectComparisonPacket(event: ChangeEvent<HTMLInputElement>, side: "baseline" | "current") {
    const file = event.target.files?.[0]; event.target.value = ""; if (!file) return;
    setComparison(null); setError(null);
    try {
      const packet = JSON.parse(await readFileAsText(file)) as unknown;
      if (side === "baseline") setBaselinePacket(packet); else setCurrentPacket(packet);
    } catch { setError(`The selected ${side} file is not valid JSON.`); }
  }

  async function comparePackets() {
    if (!baselinePacket || !currentPacket) return;
    setComparing(true); setComparison(null); setError(null);
    try {
      const response = await fetch("/api/research-evidence-audit-packet/compare", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ baseline: baselinePacket, current: currentPacket }) });
      if (response.status === 401) { window.location.href = "/login"; return; }
      if (!response.ok) { setError("The selected audit packets could not be compared."); return; }
      setComparison((await response.json()) as ComparisonResult);
    } catch { setError("The audit packet comparison service is unavailable."); } finally { setComparing(false); }
  }

  if (loading) return <section className="dashboard-state" aria-live="polite">Loading provenance projects…</section>;
  if (error && !projectId) return <section className="dashboard-state" role="alert">{error}</section>;
  if (!projectId) return null;

  return (
    <section className="research-provenance-section">
      <div className="research-section-heading">
        <div><p className="eyebrow">PROJECT EVIDENCE TRAIL</p><h2>Provenance ledger</h2></div>
        <div>
          <label>Research project<select aria-label="Provenance research project" value={projectId} onChange={(event) => setProjectId(Number(event.target.value))}>{projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}</select></label>
          <button type="button" onClick={downloadAuditPacket} disabled={downloading}>{downloading ? "Preparing packet…" : "Download audit packet"}</button>
          <label><span>{verifying ? "Verifying packet…" : "Verify audit packet"}</span><input aria-label="Verify audit packet" type="file" accept="application/json,.json" onChange={verifyAuditPacket} disabled={verifying} /></label>
        </div>
      </div>
      {error ? <p role="alert" className="form-message">{error}</p> : null}
      {verification ? <section className="dashboard-panel" aria-labelledby="audit-verification-title"><div className="panel-heading"><div><p className="eyebrow">AUDIT PACKET VERIFICATION</p><h3 id="audit-verification-title">{verification.valid ? "Packet passed verification" : "Packet requires review"}</h3><p className="muted">{verification.disclaimer}</p></div></div><div className="activity-list">{verification.checks.map((check) => <article className="activity-card" key={check.code}><span>{check.passed ? "PASS" : "FAIL"}</span><div><strong>{check.code.replaceAll("_", " ")}</strong><p>{check.message}</p></div></article>)}</div><p className="muted"><strong>Computed SHA-256:</strong> {verification.computed_sha256}</p></section> : null}
      <section className="dashboard-panel" aria-labelledby="audit-comparison-title">
        <div className="panel-heading"><div><p className="eyebrow">AUDIT PACKET COMPARISON</p><h3 id="audit-comparison-title">Compare evidence history</h3><p className="muted">Select a baseline packet and a current packet. Files are verified and compared transiently; they are not imported or stored.</p></div></div>
        <div className="form-grid">
          <label>Baseline packet<input aria-label="Baseline audit packet" type="file" accept="application/json,.json" onChange={(event) => void selectComparisonPacket(event, "baseline")} /></label>
          <label>Current packet<input aria-label="Current audit packet" type="file" accept="application/json,.json" onChange={(event) => void selectComparisonPacket(event, "current")} /></label>
        </div>
        <button type="button" onClick={comparePackets} disabled={!baselinePacket || !currentPacket || comparing}>{comparing ? "Comparing packets…" : "Compare packets"}</button>
        {comparison ? <div><p className="muted">{comparison.disclaimer}</p><div className="metric-grid"><article><strong>{comparison.summary.added}</strong><span>Added</span></article><article><strong>{comparison.summary.removed}</strong><span>Removed</span></article><article><strong>{comparison.summary.changed}</strong><span>Changed</span></article><article><strong>{comparison.summary.unchanged}</strong><span>Unchanged</span></article></div><p><strong>{comparison.comparable ? "Packets verified and comparable." : "One or both packets require verification review."}</strong></p>{comparison.project_changes.length ? <p>Project fields changed: {comparison.project_changes.join(", ")}</p> : null}{comparison.summary_changes.length ? <p>Summary fields changed: {comparison.summary_changes.join(", ")}</p> : null}<div className="activity-list">{comparison.changes.filter((change) => change.classification !== "unchanged").map((change) => <article className="activity-card" key={change.event_id}><span>{change.classification.toUpperCase()}</span><div><strong>{change.event_type.replaceAll("_", " ")} · evidence {change.evidence_id}</strong><p>{change.explanation}</p></div></article>)}</div></div> : null}
      </section>
      <ResearchProvenancePanel projectId={projectId} />
    </section>
  );
}
