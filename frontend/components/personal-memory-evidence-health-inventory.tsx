"use client";

import { useCallback, useEffect, useState } from "react";

type Classification = "strong" | "adequate" | "weak" | "contested" | "unavailable" | "unsupported";

type Health = {
  classification: Classification;
  total_count: number;
  available_count: number;
  unavailable_count: number;
  approved_count: number;
  needs_review_count: number;
  supporting_count: number;
  contradicting_count: number;
  average_credibility: number | null;
  average_freshness: number | null;
  average_confidence: number | null;
  reasons: string[];
  recommended_actions: string[];
};

type InventoryItem = {
  memory_id: number;
  project_id: number;
  summary: string;
  statement: string;
  category: string;
  status: string;
  confidence: number;
  updated_at: string;
  health: Health;
};

type Inventory = {
  project_id: number | null;
  classification: Classification | null;
  total_count: number;
  by_classification: Record<string, number>;
  items: InventoryItem[];
};

const classifications: Classification[] = ["contested", "unavailable", "unsupported", "weak", "adequate", "strong"];

function openRecord(item: InventoryItem) {
  const inventory = document.querySelector('[aria-label="Personal memory inventory"]');
  const buttons = Array.from(inventory?.querySelectorAll("button") ?? []);
  const target = buttons.find((button) => button.textContent?.includes(item.summary));
  target?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  window.setTimeout(() => {
    document.querySelector('[aria-label="Selected memory"]')?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, 0);
}

export function PersonalMemoryEvidenceHealthInventory() {
  const [projectId, setProjectId] = useState("");
  const [classification, setClassification] = useState<Classification | "">("");
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (nextProjectId = projectId, nextClassification = classification) => {
    const params = new URLSearchParams();
    if (nextProjectId.trim()) params.set("project_id", nextProjectId.trim());
    if (nextClassification) params.set("classification", nextClassification);
    const response = await fetch(`/api/personal-memory/evidence-health${params.size ? `?${params}` : ""}`, { cache: "no-store" });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    if (!response.ok) throw new Error("inventory");
    setInventory((await response.json()) as Inventory);
  }, [classification, projectId]);

  useEffect(() => {
    void load("", "").catch(() => setError("Evidence health triage could not be loaded."));
  }, [load]);

  async function applyFilters() {
    setBusy(true);
    setError(null);
    try {
      await load();
    } catch {
      setError("Evidence health triage could not be filtered.");
    } finally {
      setBusy(false);
    }
  }

  async function clearFilters() {
    setProjectId("");
    setClassification("");
    setBusy(true);
    setError(null);
    try {
      await load("", "");
    } catch {
      setError("Evidence health triage could not be refreshed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="dashboard-panel" aria-labelledby="evidence-health-inventory-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">EVIDENCE REVIEW TRIAGE</p>
          <h2 id="evidence-health-inventory-title">Records that need attention</h2>
        </div>
      </div>
      {error ? <p role="alert">{error}</p> : null}
      <form className="action-list" aria-label="Evidence health inventory filters" onSubmit={(event) => { event.preventDefault(); void applyFilters(); }}>
        <label>Project ID<input aria-label="Evidence health project ID" value={projectId} onChange={(event) => setProjectId(event.target.value)} inputMode="numeric" placeholder="All projects" /></label>
        <label>Health classification<select aria-label="Evidence health classification" value={classification} onChange={(event) => setClassification(event.target.value as Classification | "")}><option value="">All classifications</option>{classifications.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <button type="submit" disabled={busy}>Apply triage filters</button>
        <button type="button" disabled={busy} onClick={() => void clearFilters()}>Clear triage filters</button>
      </form>
      {!inventory ? <p className="muted">Loading evidence health triage…</p> : (
        <>
          <div className="metric-grid" aria-label="Evidence health classification counts">
            {classifications.map((value) => <article className="metric-card" key={value}><span>{value}</span><strong>{inventory.by_classification[value] ?? 0}</strong></article>)}
          </div>
          <div className="action-list" aria-label="Evidence health inventory">
            {inventory.items.length ? inventory.items.map((item) => (
              <button type="button" className="action-card" key={item.memory_id} onClick={() => openRecord(item)}>
                <div>
                  <span className={`priority priority-${item.health.classification === "strong" ? "low" : item.health.classification === "adequate" ? "medium" : "high"}`}>{item.health.classification}</span>
                  <h3>{item.summary}</h3>
                  <p>{item.statement}</p>
                  <p className="muted">Project {item.project_id} · {item.category} · {item.health.available_count}/{item.health.total_count} evidence available · {item.health.needs_review_count} need review</p>
                  {item.health.recommended_actions[0] ? <p>{item.health.recommended_actions[0]}</p> : null}
                </div>
                <span aria-hidden="true">→</span>
              </button>
            )) : <p className="muted">No saved records match the current evidence-health filters.</p>}
          </div>
        </>
      )}
    </section>
  );
}
