"use client";

import { useState } from "react";
import type { ChangeEvent } from "react";

type PacketInput = {
  content_sha256: string;
  content: Record<string, unknown>;
};
type Difference = {
  path: string;
  kind: "added" | "removed" | "changed";
};
type ReportContent = {
  schema_version: string;
  report_type: string;
  status: "identical" | "different" | "unsupported";
  left_hash_matches: boolean;
  right_hash_matches: boolean;
  added_count: number;
  removed_count: number;
  changed_count: number;
  differences: Difference[];
  detail: string;
  disclaimer: string;
};
type ReportResult = { report_sha256: string; content: ReportContent };

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

export function ResearchPacketComparisonReportWorkspace() {
  const [leftText, setLeftText] = useState("");
  const [rightText, setRightText] = useState("");
  const [result, setResult] = useState<ReportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  async function loadFile(
    event: ChangeEvent<HTMLInputElement>,
    side: "left" | "right",
  ) {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const value = await readFileText(file);
      if (side === "left") {
        setLeftText(value);
      } else {
        setRightText(value);
      }
      setResult(null);
      setError(null);
    } catch {
      setError("The selected packet file could not be read.");
    }
  }

  async function createReport() {
    let left: PacketInput;
    let right: PacketInput;

    try {
      left = parsePacket(leftText);
      right = parsePacket(rightText);
    } catch {
      setResult(null);
      setError(
        "Enter two valid exported packets containing content_sha256 and content.",
      );
      return;
    }

    setExporting(true);
    try {
      const response = await fetch("/api/research-packet-comparison-report", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ left, right }),
      });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) throw new Error("Report request failed");
      setResult((await response.json()) as ReportResult);
      setError(null);
    } catch {
      setResult(null);
      setError("The comparison report could not be created.");
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
    anchor.download = `lionsforge-packet-comparison-${result.report_sha256.slice(0, 12)}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="research-provenance-section">
      <div className="research-section-heading">
        <div>
          <p className="eyebrow">RESEARCH WORKSPACE</p>
          <h1>Packet comparison report</h1>
          <p className="muted">
            Create a portable, hash-addressed JSON record of deterministic packet
            differences.
          </p>
        </div>
      </div>

      <div className="dashboard-grid">
        <section className="dashboard-panel">
          <h2>Earlier packet</h2>
          <label>
            Earlier packet JSON
            <textarea
              aria-label="Earlier packet JSON"
              rows={16}
              value={leftText}
              onChange={(event) => setLeftText(event.target.value)}
            />
          </label>
          <label>
            Load earlier JSON
            <input
              aria-label="Load earlier JSON"
              type="file"
              accept="application/json,.json"
              onChange={(event) => void loadFile(event, "left")}
            />
          </label>
        </section>

        <section className="dashboard-panel">
          <h2>Later packet</h2>
          <label>
            Later packet JSON
            <textarea
              aria-label="Later packet JSON"
              rows={16}
              value={rightText}
              onChange={(event) => setRightText(event.target.value)}
            />
          </label>
          <label>
            Load later JSON
            <input
              aria-label="Load later JSON"
              type="file"
              accept="application/json,.json"
              onChange={(event) => void loadFile(event, "right")}
            />
          </label>
        </section>
      </div>

      <button
        type="button"
        disabled={exporting}
        onClick={() => void createReport()}
      >
        {exporting ? "Creating…" : "Create comparison report"}
      </button>

      {error ? (
        <p role="alert" className="form-message">
          {error}
        </p>
      ) : null}

      {result ? (
        <section
          className="dashboard-panel"
          aria-label="Comparison report result"
        >
          <h2>Report status: {result.content.status}</h2>
          <p>{result.content.detail}</p>
          <p>
            Report SHA-256: <code>{result.report_sha256}</code>
          </p>
          <p>
            Earlier hash matches: {result.content.left_hash_matches ? "yes" : "no"}
          </p>
          <p>
            Later hash matches: {result.content.right_hash_matches ? "yes" : "no"}
          </p>
          <p>
            Added: {result.content.added_count} · Removed: {result.content.removed_count}
            {" · "}
            Changed: {result.content.changed_count}
          </p>
          {result.content.differences.length ? (
            <ul>
              {result.content.differences.map((item) => (
                <li key={`${item.kind}:${item.path}`}>
                  <code>{item.path}</code> — {item.kind}
                </li>
              ))}
            </ul>
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
