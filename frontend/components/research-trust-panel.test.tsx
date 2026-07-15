import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchTrustPanel } from "@/components/research-trust-panel";
import type { ResearchTrustIndex } from "@/lib/research-trust-index";

const trustIndex: ResearchTrustIndex = {
  project_id: 7,
  overall_score: 84.2,
  confidence_level: "moderate",
  evidence_count: 12,
  supporting_count: 9,
  contradicting_count: 2,
  approved_count: 8,
  conflict_count: 1,
  review_event_count: 14,
  reviewed_evidence_count: 9,
  review_reversal_count: 2,
  components: [
    {
      key: "validation_stability",
      label: "Validation Stability",
      score: 78,
      weight: 0.15,
      weighted_score: 11.7,
      explanation: "Nine evidence records have review history; two reversals were detected.",
      recommendations: ["Resolve frequently reversed evidence decisions."],
    },
  ],
  strengths: ["Evidence Quality"],
  limitations: ["One unresolved conflict remains."],
  recommended_actions: ["Resolve frequently reversed evidence decisions."],
  methodology_version: "rti-v2",
};

function response(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("ResearchTrustPanel", () => {
  it("renders RTI v2 validation stability, reversals, conflicts, and actions", async () => {
    const fetchMock = vi.fn(() => response(trustIndex));
    vi.stubGlobal("fetch", fetchMock);

    render(<ResearchTrustPanel projectId={7} />);

    expect(await screen.findByText("84%")).toBeInTheDocument();
    expect(screen.getByText("78%")).toBeInTheDocument();
    expect(screen.getByText("rti-v2", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Resolve frequently reversed evidence decisions.")).toBeInTheDocument();
    expect(screen.getByText("2", { selector: "strong" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/research-trust-index/projects/7",
      expect.objectContaining({ cache: "no-store", signal: expect.any(AbortSignal) }),
    );
  });

  it("replaces project trust data when the selected project changes", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const projectId = String(input).endsWith("/8") ? 8 : 7;
      return response({ ...trustIndex, project_id: projectId, overall_score: projectId === 8 ? 91 : 84.2 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const { rerender } = render(<ResearchTrustPanel projectId={7} />);
    expect(await screen.findByText("84%")).toBeInTheDocument();

    rerender(<ResearchTrustPanel projectId={8} />);
    expect(await screen.findByText("91%")).toBeInTheDocument();
    expect(screen.queryByText("84%")).not.toBeInTheDocument();
  });

  it("aborts an active trust request when unmounted", async () => {
    const pending = deferred<Awaited<ReturnType<typeof response>>>();
    let requestSignal: AbortSignal | undefined;
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      requestSignal = init?.signal ?? undefined;
      return pending.promise;
    }));

    const { unmount } = render(<ResearchTrustPanel projectId={7} />);
    await waitFor(() => expect(requestSignal).toBeDefined());

    unmount();
    expect(requestSignal?.aborted).toBe(true);
  });

  it("shows a safe project trust error without exposing stale data", async () => {
    vi.stubGlobal("fetch", vi.fn(() => response(null, 404)));

    render(<ResearchTrustPanel projectId={7} />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Research trust data is not available for this project.",
    );
    expect(screen.queryByText("84%")).not.toBeInTheDocument();
  });
});
