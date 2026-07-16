import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MarketLearningEvidencePanel } from "@/components/market-learning-evidence-panel";

const session = {
  id: 7,
  account_id: 3,
  scenario_name: "bear_market",
  steps: 20,
  seed: 17,
  risk_tier: "high",
  projected_return: "-0.0825",
  learner_reflection: "Concentration increased modeled downside.",
  status: "completed",
  completed_at: "2026-07-16T00:00:00Z",
};

const project = {
  id: 4,
  title: "Risk research",
  description: null,
  objective: "Validate simulation reasoning",
  status: "active",
  created_at: "2026-07-15T00:00:00Z",
  updated_at: "2026-07-15T00:00:00Z",
};

const evidence = {
  link_id: 11,
  session_id: 7,
  project_id: 4,
  evidence: {
    id: 9,
    project_id: 4,
    claim: "The simulation demonstrated that concentration amplified modeled downside risk.",
    validation_status: "needs_review",
    reviewer_notes: "Compare an additional scenario.",
    provenance: { excluded_from_empirical_evidence: true },
  },
  scenario_name: "bear_market",
  risk_tier: "high",
  simulated_projected_return: "-0.0825",
  learner_reflection: "Concentration increased modeled downside.",
  completed_at: "2026-07-16T00:00:00Z",
  classification: "simulated_educational_evidence",
  next_reflection_prompt: "Compare an additional scenario before refining the claim.",
  disclaimer: "This is not real-world empirical evidence or investment performance.",
};

function response(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

function initialFetch(historyStatus = 404) {
  return vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/learning-sessions")) return response([session]);
    if (url.endsWith("/research-projects")) return response([project]);
    if (url.endsWith("/learning-evidence/7")) {
      return historyStatus === 404
        ? response({ detail: "Learning evidence not found" }, 404)
        : response({ evidence, reviews: [{ id: 1, evidence_id: 9, previous_status: "unverified", validation_status: "needs_review", reviewer_notes: "Compare an additional scenario.", created_at: "2026-07-16T01:00:00Z" }] });
    }
    if (url.endsWith("/learning-evidence") && init?.method === "POST") return response(evidence, 201);
    return response(null, 500);
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("MarketLearningEvidencePanel", () => {
  it("renders an eligible session and submits simulated educational evidence", async () => {
    const fetchMock = initialFetch();
    vi.stubGlobal("fetch", fetchMock);

    render(<MarketLearningEvidencePanel />);

    expect(await screen.findByText("bear market · high risk · -8.3% simulated")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Learning session"), { target: { value: "7" } });
    fireEvent.change(screen.getByLabelText("Research project"), { target: { value: "4" } });
    fireEvent.change(screen.getByLabelText("Learner claim"), { target: { value: evidence.evidence.claim } });
    fireEvent.click(screen.getByRole("button", { name: "Submit simulated evidence" }));

    expect(await screen.findByRole("status")).toHaveTextContent("submitted for review");
    expect(screen.getByText("bear market · simulated educational evidence")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/market-simulator/learning-evidence",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("renders immutable review outcomes and educational guardrails", async () => {
    vi.stubGlobal("fetch", initialFetch(200));

    render(<MarketLearningEvidencePanel />);

    expect(await screen.findByText("bear market · simulated educational evidence")).toBeInTheDocument();
    expect(screen.getByText("Compare an additional scenario.")).toBeInTheDocument();
    expect(screen.getByText("1 immutable review event")).toBeInTheDocument();
    expect(screen.getByText("Approval does not establish investment success", { exact: false })).toBeInTheDocument();
  });

  it("surfaces duplicate submission conflicts safely", async () => {
    const fetchMock = initialFetch();
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/learning-sessions")) return response([session]);
      if (url.endsWith("/research-projects")) return response([project]);
      if (url.endsWith("/learning-evidence/7")) return response({}, 404);
      if (url.endsWith("/learning-evidence") && init?.method === "POST") return response({}, 409);
      return response(null, 500);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<MarketLearningEvidencePanel />);
    await screen.findByText("bear market · high risk · -8.3% simulated");
    fireEvent.change(screen.getByLabelText("Learning session"), { target: { value: "7" } });
    fireEvent.change(screen.getByLabelText("Research project"), { target: { value: "4" } });
    fireEvent.change(screen.getByLabelText("Learner claim"), { target: { value: evidence.evidence.claim } });
    fireEvent.click(screen.getByRole("button", { name: "Submit simulated evidence" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("already been submitted");
  });

  it("aborts loading requests when unmounted", async () => {
    const signals: AbortSignal[] = [];
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.signal) signals.push(init.signal);
      return new Promise(() => undefined);
    }));

    const { unmount } = render(<MarketLearningEvidencePanel />);
    await waitFor(() => expect(signals.length).toBeGreaterThan(0));
    unmount();
    expect(signals.every((signal) => signal.aborted)).toBe(true);
  });
});
