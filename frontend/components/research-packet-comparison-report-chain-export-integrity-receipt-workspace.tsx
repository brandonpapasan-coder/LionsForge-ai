"use client";

import { useState } from "react";
import type { ChangeEvent } from "react";

type VerificationReportInput = {
  verification_report_sha256: string;
  content: Record<string, unknown>;
};

type IntegrityReceipt = {
  integrity_receipt_sha256: string;
  content: {
    schema_version: string;
    report_type: string;
    integrity_status: "matching" | "changed" | "unsupported";
    supplied_sha256: string;
    computed_sha256: string;
    source_schema_version: string | null;
    source_report_type: string | null;
    detail: string;
    disclaimer: string;
  };
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
    throw new Error("Invalid verification report");
  }
  return {
    verification_report_sha256: parsed.verification_report_sha256,
    content: parsed.content as Record<string, unknown>,
  };
}

export function ResearchPacketComparisonReportChainExportIntegrityReceiptWorkspace() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<IntegrityReceipt | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

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

  async function exportReceipt() {
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

    setExporting(true);
    try {
      const response = await fetch(
        "/api/research-packet-comparison-report-chain-export-integrity-receipt",
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
      if (!response.ok) throw new Error("Receipt export failed");
      setResult((await response.json()) as IntegrityReceipt);
      setError(null);
    } catch {
      setResult(null);
      setError("The integrity receipt could not be exported.");
    } finally {
      setExporting(false);
    }
  }

  function downloadReceipt() {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `lionsforge-chain-integrity-receipt-${result.integrity_receipt_sha256.slice(0, 12)}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="research-provenance-section">
      <div className="research-section-heading">
        <div>
          <p className="eyebrow">RESEARCH WORKSPACE</p>
          <h1>Chain verification integrity receipt</h1>
          <p className="muted">
            Export a portable, hash-addressed JSON receipt for a standalone chain-verification report integrity check.
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
            placeholder="Paste a LionsForge chain-verification report here"
          />
        </label>
        <label>
          Load verification report JSON
          <input
            aria-label="Load verification report JSON"
            type="file"
            accept="application/json,.json"
            onChange={(event) => void loadFile(event)}
          />
        </label>
        <button type="button" disabled={exporting} onClick={() => void exportReceipt()}>
          {exporting ? "Exporting…" : "Export integrity receipt"}
        </button>
      </section>

      {error ? (
        <p role="alert" className="form-message">
          {error}
        </p>
      ) : null}

      {result ? (
        <section className="dashboard-panel" aria-label="Integrity receipt result">
          <h2>Integrity status: {result.content.integrity_status}</h2>
          <p>{result.content.detail}</p>
          <p>
            Integrity receipt SHA-256: <code>{result.integrity_receipt_sha256}</code>
          </p>
          <p>
            Supplied report SHA-256: <code>{result.content.supplied_sha256}</code>
          </p>
          <p>
            Computed report SHA-256: <code>{result.content.computed_sha256}</code>
          </p>
          <p>Source schema: {result.content.source_schema_version ?? "not supplied"}</p>
          <p>Source report type: {result.content.source_report_type ?? "not supplied"}</p>
          <button type="button" onClick={downloadReceipt}>
            Download JSON receipt
          </button>
          <p className="muted">{result.content.disclaimer}</p>
        </section>
      ) : null}
    </section>
  );
}
