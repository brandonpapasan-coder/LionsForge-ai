import { render, screen, waitFor } from "@testing-library/react";

import { KnowledgeQualityDashboard } from "@/components/knowledge-quality-dashboard";

const dashboard = {
  project_id: null,
  methodology_version: "knowledge-quality-v1",
  generated_at: "2026-07-13T20:00:00Z",
  health_score: 0.82,
  health_components: {
    validation: 0.9,
    confidence: 0.8,
    evidence_coverage: 0.75,
  },
  memories: {
    total: 10,
    validated: 7,
    provisional: 2,
    contested: 1,
    superseded: 0,
    archived: 0,
    stale: 1,
  },
  evidence_total: 12,
  evidence_approved: 9,
  evidence_pending_review: 3,
  evidence_coverage_ratio: 0.75,
  average_confidence: 0.8,
  median_confidence: 0.81,
  contradiction_rate: 0.1,
  unresolved_contradictions: 1,
  federation_links: 4,
  federation_coverage_ratio: 0.4,
  missions: {},
  planning: {},
  knowledge_revision_velocity: 3,
  review_backlog: 3,
  top_risks: [
    {
      risk_type: "contested_knowledge",
      severity: 0.7,
      title: "Contested knowledge requires review",
      detail: "One contested record remains visible.",
      source_ids: [4],
    },
  ],
  top_priorities: [],
  recent_activity: [
    {
      record_type: "knowledge_memory",
      record_id: 4,
      title: "Battery storage finding",
      status: "validated",
      occurred_at: "2026-07-13T19:00:00Z",
    },
  ],
};

describe("KnowledgeQualityDashboard", () => {
  it("renders transparent quality metrics, risks, and activity", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => dashboard,
    }));

    render(<KnowledgeQualityDashboard />);

    expect(screen.getByText("Loading institutional knowledge health…")).toBeInTheDocument();
    expect(await screen.findByText("82%")).toBeInTheDocument();
    expect(screen.getByText("Contested knowledge requires review")).toBeInTheDocument();
    expect(screen.getByText("Battery storage finding")).toBeInTheDocument();
    expect(screen.getByText(/does not validate research/i)).toBeInTheDocument();
  });

  it("shows an honest no-baseline state for empty data", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        ...dashboard,
        health_score: 0,
        memories: { ...dashboard.memories, total: 0, validated: 0, provisional: 0, contested: 0 },
        evidence_total: 0,
        evidence_approved: 0,
        evidence_pending_review: 0,
        top_risks: [],
        recent_activity: [],
      }),
    }));

    render(<KnowledgeQualityDashboard />);

    expect(await screen.findByText("No baseline")).toBeInTheDocument();
    expect(screen.getByText(/No research baseline exists yet/i)).toBeInTheDocument();
  });

  it("exposes API failures through an alert", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));

    render(<KnowledgeQualityDashboard />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Institutional knowledge quality could not be loaded.");
    });
  });
});
