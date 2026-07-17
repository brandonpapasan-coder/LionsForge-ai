"use client";

import { useState } from "react";
import type { ChangeEvent } from "react";

type PacketInput = {
  content_sha256: string;
  content: Record<string, unknown>;
};

type ReportInput = {
  report_sha256: string;
  content: Record<string, unknown>;
};

type VerificationContent = {
  schema_version: string;
  report_type: string;
  chain_status: "consistent" | "inconsistent" | "unsupported";
  left_hash_matches: boolean;
  right_hash_matches: boolean;
  comparison_report_hash_matches: boolean;
  failed_checks: string[];
  detail: string;
  disclaimer: string;
};

type VerificationReport = {
  verification_report_sha256: string;
  content: VerificationContent;
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

function parsePacket(text: string): PacketInput {
  const parsed = JSON.parse(text) as Partial<PacketInput>;
  if (
    typeof parsed.content_sha256 !== "string" ||
    !parsed.content ||
    typeof parsed.content !== "object"
  ) {
    throw new Error("Invalid packet");
  }
  return {
    content_sha256: parsed.content_sha256,
    content: parsed.content as Record<string, unknown>,
  };
}

function parseReport(text: string): ReportInput {
  const parsed = JSON.parse(text) as Partial<ReportInput>;
  if (
    typeof parsed.report_sha256 !== "string" ||
    !parsed.content ||
    typeof parsed.content !== "object"
  ) {
    throw new Error("Invalid report");
  }
  return {
    report_sha256: parsed.report_sha256,
    content: parsed.content as Record<string, unknown>,
  };
}

export function ResearchPacketComparisonReportChainExportWorkspace() {
  const [leftText, setLeftText] = useState("");
  const [rightText, setRightText] = useState("");
  const [reportText, setReportText] = useState("");
  const [result, setResult] = useState<VerificationReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  async function loadFile(
    event: ChangeEvent<HTMLInputElement>,
    target: "left" | "right" | "report",
  ) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const value = await readFileText(file);
      if (target === "left") setLeftText(value);
      else if (target === "right") setRightText(value);
      else setReportText(value);
      setResult(null);
      setError(null);
    } catch {
      setError("The selected JSON file could not be read.");
    }
  }

  async function exportVerificationReport() {
    let left: PacketInput;
    let right: PacketInput;
    let report: ReportInput;
    try {
      left = parsePacket(leftText);
      right = parsePacket(rightText);
      report = parseReport(reportText);
    } catch {
      setResult(null);
      setError("Enter two valid exported packets and one valid comparison report.");
      return;
    }

    setExporting(true);
    try {
      const response = await fetch(
        "/api/research-packet-comparison-report-chain-export",
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ left, right, report }),
        },
      );
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) throw new Error("Export failed");
      setResult((await response.json()) as VerificationReport);
      setError(null);
    } catch {
      setResult(null);
      setError("The chain verification report could not be exported.");
    } finally {
      setExporting(false);
    }
  }

  function downloadReport() {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `lionsforge-chain-verification-${result.verification_report_sha256.slice(0, 12)}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="research-provenance-section">
      <div className="research-section-heading">
        <div>
          <p className="eyebrow">RESEARCH WORKSPACE</p>
          <h1>Comparison chain verification report</h1>
          <p className="muted">
            Export a portable, hash-addressed JSON record of a two-packet comparison integrity-chain verification.
          </p>
        </div>
      </div>

      <div className="dashboard-grid">
        {[
          ["Earlier packet", "Earlier packet JSON", leftText, setLeftText, "left"],
          ["Later packet", "Later packet JSON", rightText, setRightText, "right"],
          ["Comparison report", "Comparison report JSON", reportText, setReportText, "report"],
        ].map(([title, label, value, setter, target]) => (
          <section className="dashboard-panel" key={String(target)}>
            <h2>{String(title)}</h2>
            <label>
              {String(label)}
              <textarea
                aria-label={String(label)}
                rows={14}
                value={String(value)}
                onChange={(event) =>
                  (setter as (next: string) => void)(event.target.value)
                }
              />
            </label>
            <label>
              Load {String(title).toLowerCase()} JSON
              <input
                aria-label={`Load ${String(title).toLowerCase()} JSON`}
                type="file"
                accept="application/json,.json"
                onChange={(event) =>
                  void loadFile(
                    event,
                    target as "left" | "right" | "report",
                  )
                }
              />
            </label>
          </section>
        ))}
      </div>

      <button
        type="button"
        disabled={exporting}
        onClick={() => void exportVerificationReport()}
      >
        {exporting ? "Exporting…" : "Export verification report"}
      </button>

      {error ? (
        <p role="alert" className="form-message">
          {error}
        </p>
      ) : null}

      {result ? (
        <section className="dashboard-panel" aria-label="Verification report result">
          <h2>Chain status: {result.content.chain_status}</h2>
          <p>{result.content.detail}</p>
          <p>
            Verification report SHA-256: <code>{result.verification_report_sha256}</code>
          </p>
          <p>Earlier packet hash matches: {result.content.left_hash_matches ? "yes" : "no"}</p>
          <p>Later packet hash matches: {result.content.right_hash_matches ? "yes" : "no"}</p>
          <p>Comparison report hash matches: {result.content.comparison_report_hash_matches ? "yes" : "no"}</p>
          {result.content.failed_checks.length ? (
            <>
              <h3>Failed checks</h3>
              <ul>
                {result.content.failed_checks.map((check) => (
                  <li key={check}>
                    <code>{check}</code>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          <button type="button" onClick={downloadReport}>
            Download JSON report
          </button>
          <p className="muted">{result.content.disclaimer}</p>
        </section>
      ) : null}
    </section>
  );
}
