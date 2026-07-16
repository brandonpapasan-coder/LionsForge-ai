"use client";

import { ChangeEvent, useState } from "react";

type IntegrityResult = {
  status: "matching" | "changed" | "unsupported";
  supplied_sha256: string;
  computed_sha256: string;
  schema_version: string | null;
  supported_schema_versions: string[];
  detail: string;
  disclaimer: string;
};

type PacketInput = { content_sha256: string; content: Record<string, unknown> };

// Prefer the modern File.text API while retaining a FileReader fallback for older browsers and test environments.
function readFileText(file: File): Promise<string> {
  if (typeof file.text === "function") return file.text();

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error ?? new Error("File read failed"));
    reader.onload = () => {
      if (typeof reader.result === "string") resolve(reader.result);
      else reject(new Error("File did not contain text"));
    };
    reader.readAsText(file);
  });
}

export function ResearchPacketIntegrityChecker() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<IntegrityResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  async function verify() {
    let packet: PacketInput;
    try {
      const parsed = JSON.parse(text) as Partial<PacketInput>;
      if (typeof parsed.content_sha256 !== "string" || !parsed.content || typeof parsed.content !== "object") throw new Error();
      packet = { content_sha256: parsed.content_sha256, content: parsed.content as Record<string, unknown> };
    } catch {
      setResult(null);
      setError("Enter a valid exported packet containing content_sha256 and content.");
      return;
    }

    setChecking(true);
    try {
      const response = await fetch("/api/research-packet-integrity", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(packet),
      });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) throw new Error();
      setResult((await response.json()) as IntegrityResult);
      setError(null);
    } catch {
      setResult(null);
      setError("The packet integrity check could not be completed.");
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
      setError("The selected packet file could not be read.");
    }
  }

  return (
    <section className="research-provenance-section">
      <div className="research-section-heading">
        <div>
          <p className="eyebrow">RESEARCH WORKSPACE</p>
          <h1>Packet integrity checker</h1>
          <p className="muted">Recompute an exported packet&apos;s canonical SHA-256 value and compare it with the supplied value.</p>
        </div>
      </div>
      <section className="dashboard-panel">
        <label>
          Packet JSON
          <textarea aria-label="Packet JSON" rows={18} value={text} onChange={(event) => setText(event.target.value)} placeholder="Paste a LionsForge research packet here" />
        </label>
        <label>
          Load JSON packet
          <input aria-label="Load JSON packet" type="file" accept="application/json,.json" onChange={(event) => void loadFile(event)} />
        </label>
        <button type="button" disabled={checking} onClick={() => void verify()}>
          {checking ? "Checking…" : "Check integrity"}
        </button>
      </section>
      {error ? <p role="alert" className="form-message">{error}</p> : null}
      {result ? (
        <section className="dashboard-panel" aria-label="Integrity result">
          <h2>Integrity status: {result.status}</h2>
          <p>{result.detail}</p>
          <p>Schema: {result.schema_version ?? "not supplied"}</p>
          <p>Supplied SHA-256: <code>{result.supplied_sha256}</code></p>
          <p>Computed SHA-256: <code>{result.computed_sha256}</code></p>
          {result.status === "unsupported" ? <p>Supported schemas: {result.supported_schema_versions.join(", ")}</p> : null}
          <p className="muted">{result.disclaimer}</p>
        </section>
      ) : null}
    </section>
  );
}
