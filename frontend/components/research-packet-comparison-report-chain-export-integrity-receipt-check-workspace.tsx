"use client";

import { useState } from "react";
import type { ChangeEvent } from "react";

type IntegrityReceiptInput = {
  integrity_receipt_sha256: string;
  content: Record<string, unknown>;
};

type IntegrityCheckResult = {
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

function parseReceipt(text: string): IntegrityReceiptInput {
  const parsed = JSON.parse(text) as Partial<IntegrityReceiptInput>;
  if (
    typeof parsed.integrity_receipt_sha256 !== "string" ||
    !parsed.content ||
    typeof parsed.content !== "object"
  ) {
    throw new Error("Invalid integrity receipt");
  }
  return {
    integrity_receipt_sha256: parsed.integrity_receipt_sha256,
    content: parsed.content as Record<string, unknown>,
  };
}

export function ResearchPacketComparisonReportChainExportIntegrityReceiptCheckWorkspace() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<IntegrityCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  async function loadFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      setText(await readFileText(file));
      setResult(null);
      setError(null);
    } catch {
      setError("The selected integrity receipt file could not be read.");
    }
  }

  async function checkReceipt() {
    let receipt: IntegrityReceiptInput;
    try {
      receipt = parseReceipt(text);
    } catch {
      setResult(null);
      setError(
        "Enter a valid integrity receipt containing integrity_receipt_sha256 and content.",
      );
      return;
    }

    setChecking(true);
    try {
      const response = await fetch(
        "/api/research-packet-comparison-report-chain-export-integrity-receipt-check",
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(receipt),
        },
      );
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) throw new Error("Integrity check failed");
      setResult((await response.json()) as IntegrityCheckResult);
      setError(null);
    } catch {
      setResult(null);
      setError("The integrity receipt could not be checked.");
    } finally {
      setChecking(false);
    }
  }

  return (
    <section className="research-provenance-section">
      <div className="research-section-heading">
        <div>
          <p className="eyebrow">RESEARCH WORKSPACE</p>
          <h1>Chain verification integrity receipt checker</h1>
          <p className="muted">
            Recompute the canonical SHA-256 for a downloaded integrity receipt and compare it with the supplied value.
          </p>
        </div>
      </div>

      <section className="dashboard-panel">
        <label>
          Integrity receipt JSON
          <textarea
            aria-label="Integrity receipt JSON"
            rows={18}
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Paste a LionsForge chain-verification integrity receipt here"
          />
        </label>
        <label>
          Load integrity receipt JSON
          <input
            aria-label="Load integrity receipt JSON"
            type="file"
            accept="application/json,.json"
            onChange={(event) => void loadFile(event)}
          />
        </label>
        <button type="button" disabled={checking} onClick={() => void checkReceipt()}>
          {checking ? "Checking…" : "Check integrity receipt"}
        </button>
      </section>

      {error ? (
        <p role="alert" className="form-message">
          {error}
        </p>
      ) : null}

      {result ? (
        <section className="dashboard-panel" aria-label="Integrity check result">
          <h2>Integrity status: {result.status}</h2>
          <p>{result.detail}</p>
          <p>
            Supplied receipt SHA-256: <code>{result.supplied_sha256}</code>
          </p>
          <p>
            Computed receipt SHA-256: <code>{result.computed_sha256}</code>
          </p>
          <p>Schema version: {result.schema_version ?? "not supplied"}</p>
          <p>Receipt type: {result.report_type ?? "not supplied"}</p>
          <p className="muted">{result.disclaimer}</p>
        </section>
      ) : null}
    </section>
  );
}
