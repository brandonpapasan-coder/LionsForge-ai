"use client";

import { FormEvent, useState } from "react";

import type { GeneratedResearchReport } from "@/lib/research";

export function ResearchReportForm() {
  const [message, setMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage(null);
    const form = new FormData(event.currentTarget);
    const symbol = String(form.get("symbol") ?? "").trim().toUpperCase();

    try {
      const response = await fetch("/api/research/reports", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ symbol }),
      });
      const payload = (await response.json()) as GeneratedResearchReport | { detail?: string };
      if (!response.ok) {
        setMessage("detail" in payload ? payload.detail ?? "Unable to create report." : "Unable to create report.");
        return;
      }
      const report = payload as GeneratedResearchReport;
      setMessage(`Created ${report.title} with ${report.metadata.confidence_level} confidence.`);
      event.currentTarget.reset();
    } catch {
      setMessage("The research service is unavailable.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="research-form" onSubmit={handleSubmit}>
      <label>
        Company symbol
        <input name="symbol" required minLength={1} maxLength={16} placeholder="AAPL" />
      </label>
      <button type="submit" disabled={submitting}>
        {submitting ? "Generating..." : "Generate saved report"}
      </button>
      {message ? <p role="status">{message}</p> : null}
    </form>
  );
}
