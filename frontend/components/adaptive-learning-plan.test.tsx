import React from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AdaptiveLearningPlan } from "@/components/adaptive-learning-plan";
import type { AdaptiveLearningPlan as AdaptiveLearningPlanData } from "@/lib/education";

const activePlan: AdaptiveLearningPlanData = {
  status: "active",
  generated_from: "measured_rules",
  advisory_notice: "Advisory only.",
  items: [
    {
      sequence: 1,
      lesson_slug: "evidence-remediation",
      title: "Evidence Remediation",
      target_competency: "evidence-quality",
      recommended_difficulty: "foundation",
      priority: 100,
      state: "remediation",
      reason: "Repeated assessment failures require targeted review.",
      mastery_threshold: 80,
      prerequisite_slugs: [],
      signals: [
        {
          kind: "failure_streak",
          reference: "evidence-remediation",
          value: "3 unresolved failures",
          explanation: "Three recent attempts remain below mastery.",
          measured: true,
        },
      ],
    },
    {
      sequence: 2,
      lesson_slug: "advanced-validation",
      title: "Advanced Validation",
      target_competency: "validation",
      recommended_difficulty: "advanced",
      priority: 10,
      state: "locked",
      reason: "Complete prerequisite work first.",
      mastery_threshold: 85,
      prerequisite_slugs: ["evidence-remediation"],
      signals: [
        {
          kind: "prerequisite_status",
          reference: "evidence-remediation",
          value: "incomplete",
          explanation: "The prerequisite is not complete.",
          measured: true,
        },
      ],
    },
  ],
};

function response(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("AdaptiveLearningPlan", () => {
  it("renders prioritized remediation, locked prerequisites, and measured evidence", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response(activePlan)));
    render(<AdaptiveLearningPlan />);

    const remediation = await screen.findByLabelText("Evidence Remediation: remediation");
    expect(within(remediation).getByText("Step 1")).toBeInTheDocument();
    expect(within(remediation).getByText(/Repeated assessment failures/)).toBeInTheDocument();
    expect(within(remediation).getByText(/failure streak/)).toBeInTheDocument();

    const locked = screen.getByLabelText("Advanced Validation: locked");
    expect(within(locked).getByText(/Prerequisites: evidence remediation/)).toBeInTheDocument();
    expect(screen.getByText(/Recommendations are advisory/)).toBeInTheDocument();
  });

  it("renders the completed-curriculum state", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => response({ ...activePlan, status: "completed", items: [] })),
    );
    render(<AdaptiveLearningPlan />);

    expect(await screen.findByText(/current curriculum is complete/i)).toBeInTheDocument();
  });

  it("retries after a temporary service failure", async () => {
    const user = userEvent.setup();
    let calls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(() => {
        calls += 1;
        return calls === 1 ? response({ detail: "unavailable" }, 503) : response(activePlan);
      }),
    );
    render(<AdaptiveLearningPlan />);

    await user.click(await screen.findByRole("button", { name: "Retry learning plan" }));
    expect(await screen.findByLabelText("Evidence Remediation: remediation")).toBeInTheDocument();
    expect(calls).toBe(2);
  });
});
