import React from "react";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ReleaseCountdownPanel } from "@/components/release-countdown-panel";

const countdown = {
  overall_completion_percent: 90,
  completed_points: 90,
  remaining_points: 10,
  total_points: 100,
  completed_checkpoints: 11,
  remaining_checkpoints: 10,
  blocked_checkpoints: 1,
  external_checkpoints: 10,
  remaining_milestones: 1,
  current_blocker: "Issue #29: external staging infrastructure and GitHub environment configuration",
  next_action: "Provision the Kubernetes staging cluster and lionsforge-staging namespace.",
  phases: [
    { key: "product", label: "Product implementation", weight: 72, completed_points: 72, completion_percent: 100, state: "complete", checkpoints: [{ key: "research", label: "Research assistant workflows", state: "complete", external: false, issue_number: null }] },
    { key: "staging", label: "External staging provisioning", weight: 5, completed_points: 0, completion_percent: 0, state: "blocked", checkpoints: [{ key: "cluster", label: "Provision Kubernetes staging cluster and namespace", state: "blocked", external: true, issue_number: 29 }] },
  ],
  disclaimer: "The countdown reports verified checkpoint completion, not a calendar estimate.",
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("ReleaseCountdownPanel", () => {
  it("shows verified completion, blocker, and next release action", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => countdown }));

    render(<ReleaseCountdownPanel />);

    expect(await screen.findByText("90%")).toBeInTheDocument();
    expect(screen.getByText(/Issue #29: external staging infrastructure/)).toBeInTheDocument();
    expect(screen.getByText(/Provision the Kubernetes staging cluster/)).toBeInTheDocument();
    expect(screen.getByLabelText("Release countdown phases")).toHaveTextContent("Product implementation");
    expect(screen.getByLabelText("Release countdown phases")).toHaveTextContent("External staging provisioning");
    expect(screen.getByText(/not a calendar estimate/)).toBeInTheDocument();
  });
});
