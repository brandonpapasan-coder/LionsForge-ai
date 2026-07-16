"use client";

import { ChangeEvent, useState } from "react";

type PacketInput = { content_sha256: string; content: Record<string, unknown> };
type Difference = { path: string; kind: "added" | "removed" | "changed" };
type ComparisonResult = {
  status: "identical" | "different" | "unsupported";
  left_computed_sha256: string;
  right_computed_sha256: string;
  left_hash_matches: boolean;
  right_hash_matches: boolean;
  left_schema_version: string | null;
  right_schema_version: string | null;
  supported_schema_versions: string[];
  differences: Difference[];
  added_count: number;
  removed_count: number;
  changed_count: number;
  detail: string;
  disclaimer: string;
};

function readFileText(file: File): Promise<string> {
  if (typeof file.text === "function") return file.text();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error ?? new Error("File read failed"));
    reader.onload = () => typeof reader.result === "string" ? resolve(reader.result) : reject(new Error("File did not contain text"));
    reader.readAsText(file);
  });
}

function parsePacket(text: string): PacketInput {
  const parsed = JSON.parse(text) as Partial<PacketInput>;
  if (typeof parsed.content_sha256 !== "string" || !parsed.content || typeof parsed.content !== "object") throw new Error();
  return { content_sha256: parsed.content_sha256, content: parsed.content as Record<string, unknown> };
}

export function ResearchPacketComparisonWorkspace() {
  const [leftText, setLeftText] = useState("");
  const [rightText, setRightText] = useState("");
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [comparing, setComparing] = useState(false);

  async function loadFile(event: ChangeEvent<HTMLInputElement>, side: "left" | "right") {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const value = await readFileText(file);
      if (side === "left") setLeftText(value); else setRightText(value);
      setResult(null);
      setError(null);
    } catch {
      setError("The selected packet file could not be read.");
    }
  }

  async function compare() {
    let left: PacketInput;
    let right: PacketInput;
    try {
      left = parsePacket(leftText);
      right = parsePacket(rightText);
    } catch {
      setResult(null);
      setError("Enter two valid exported packets containing content_sha256 and content.");
      return;
    }

    setComparing(true);
    try {
      const response = await fetch("/api/research-packet-comparison", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ left, right }),
      });
      if (response.status === 401) { window.location.href = "/login"; return; }
      if (!response.ok) throw new Error();
      setResult(await response.json() as ComparisonResult);
      setError(null);
    } catch {
      setResult(null);
      setError("The packet comparison could not be completed.");
    } finally {
      setComparing(false);
    }
  }

  return <section className="research-provenance-section">
    <div className="research-section-heading"><div><p className="eyebrow">RESEARCH WORKSPACE</p><h1>Packet comparison</h1><p className="muted">Compare two exported packets and identify deterministic structural changes.</p></div></div>
    <div className="dashboard-grid">
      <section className="dashboard-panel"><h2>Earlier packet</h2><label>Earlier packet JSON<textarea aria-label="Earlier packet JSON" rows={16} value={leftText} onChange={(event) => setLeftText(event.target.value)} /></label><label>Load earlier JSON<input aria-label="Load earlier JSON" type="file" accept="application/json,.json" onChange={(event) => void loadFile(event, "left")} /></label></section>
      <section className="dashboard-panel"><h2>Later packet</h2><label>Later packet JSON<textarea aria-label="Later packet JSON" rows={16} value={rightText} onChange={(event) => setRightText(event.target.value)} /></label><label>Load later JSON<input aria-label="Load later JSON" type="file" accept="application/json,.json" onChange={(event) => void loadFile(event, "right")} /></label></section>
    </div>
    <button type="button" disabled={comparing} onClick={() => void compare()}>{comparing ? "Comparing…" : "Compare packets"}</button>
    {error ? <p role="alert" className="form-message">{error}</p> : null}
    {result ? <section className="dashboard-panel" aria-label="Comparison result"><h2>Comparison status: {result.status}</h2><p>{result.detail}</p><p>Earlier hash matches: {result.left_hash_matches ? "yes" : "no"}</p><p>Later hash matches: {result.right_hash_matches ? "yes" : "no"}</p><p>Added: {result.added_count} · Removed: {result.removed_count} · Changed: {result.changed_count}</p>{result.status === "unsupported" ? <p>Supported schemas: {result.supported_schema_versions.join(", ")}</p> : null}{result.differences.length ? <ul>{result.differences.map((item) => <li key={`${item.kind}:${item.path}`}><code>{item.path}</code> — {item.kind}</li>)}</ul> : null}<p className="muted">{result.disclaimer}</p></section> : null}
  </section>;
}
