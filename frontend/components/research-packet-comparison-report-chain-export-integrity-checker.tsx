"use client";

import { useState } from "react";
import type { ChangeEvent } from "react";

type IntegrityResult = {
  status: "matching" | "changed" | "unsupported";
  supplied_sha256: string;
  computed_sha256: string;
  schema_version: string | null;
  report_type: string | null;
  supported_schema_versions: string[];
  supported_report_types: string[];
  detail: string;
  disclaimer: string;
};

type VerificationReportInput = {
  verification_report_sha256: string;
  content: Record<string, unknown>;
};

function readFileText(file: File): Promise<string> {
  if (typeof file.text === "function") return file.text();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error ?? new Error("File read failed"));
    reader.onload = () =>
      typeof reader.result === "string"
        ? resolve(reader.result)
        : reject(new Error("File did not contain text"));
    reader.readAsText(file);
  });
}

function parseVerificationReport(text: string): VerificationReportInput {
  const parsed = JSON.parse(text) as Partial<VerificationReportInput>;
  if (
    typeof parsed.verification_report_sha256 !== "string" ||
    !parsed.content ||
    typeof parsed.content !== "object"
  ) {
    throw new Error("Invalid verification report structure");
  }
  return {
    verification_report_sha256: parsed.verification_report_sha256,
    content: parsed.content as Record<string, unknown>,
  };
}

export function ResearchPacketComparisonReportChainExportIntegrityChecker() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<IntegrityResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  async function verify() {
    let report: VerificationReportInput;
    try {
      report = parseVerificationReport(text);
    } catch {
      setResult(null);
      setError(
        "Enter a valid verification report containing verification_report_sha256 and content.",
      );
      return;
    }

    setChecking(true);
    try {
      const response = await fetch(
        "/api/research-packet-comparison-report-chain-export-integrity",
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(report),
        },
      );
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) throw new Error("Integrity request failed");
      setResult((await response.json()) as IntegrityResult);
      setError(null);
    } catch {
      setResult(null);
      setError("The verification report integrity check could not be completed.");
    } finally {
      setChecking(false);
    }
  }

  async function loadFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      setText(await readFileText(file));
      setResult(null);
      setError(null);
    } catch {
      setError("The selected verification report file could not be read.");
    }
  }

  return (
    <section className="research-provenance-section">
      <div className="research-section-heading">
        <div>
          <p className="eyebrow">RESEARCH WORKSPACE</p>
          <h1>Chain verification report integrity verifier</h1>
          <p className="muted">
            Recompute a downloaded chain-verification report&apos;s canonical
            SHA-256 value and compare it with the supplied report hash.
          </p>
        </div>
      </div>

      <section className="dashboard-panel">
        <label>
          Verification report JSON
          <textarea
            aria-label="Verification report JSON"
            rows={18}
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Paste a LionsForge chain verification report here"
          />
        </label>
        <label>
          Load verification report
          <input
            aria-label="Load verification report"
            type="file"
            accept="application/json,.json"
            onChange={(event) => void loadFile(event)}
          />
        </label>
        <button type="button" disabled={checking} onClick={() => void verify()}>
          {checking ? "Checking…" : "Check report integrity"}
        </button>
      </section>

      {error ? (
        <p role="alert" className="form-message">
          {error}
        </p>
      ) : null}

      {result ? (
        <section className="dashboard-panel" aria-label="Verification report integrity result">
          <h2>Integrity status: {result.status}</h2>
          <p>{result.detail}</p>
          <p>Schema: {result.schema_version ?? "not supplied"}</p>
          <p>Report type: {result.report_type ?? "not supplied"}</p>
          <p>Supplied SHA-256: <code>{result.supplied_sha256}</code></p>
          <p>Computed SHA-256: <code>{result.computed_sha256}</code></p>
          {result.status === "unsupported" ? (
            <>
              <p>Supported schemas: {result.supported_schema_versions.join(", ")}</p>
              <p>Supported report types: {result.supported_report_types.join(", ")}</p>
            </>
          ) : null}
          <p className="muted">{result.disclaimer}</p>
        </section>
      ) : null}
    </section>
  );
}
