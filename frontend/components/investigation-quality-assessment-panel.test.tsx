import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InvestigationQualityAssessmentPanel } from "@/components/investigation-quality-assessment-panel";

describe("InvestigationQualityAssessmentPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("aborts the initial quality assessment request when the panel unmounts", () => {
    let requestSignal: AbortSignal | undefined;
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      requestSignal = init?.signal as AbortSignal | undefined;
      return new Promise<Response>(() => undefined);
    }));

    const { unmount } = render(<InvestigationQualityAssessmentPanel investigationId={4} />);

    expect(requestSignal?.aborted).toBe(false);
    unmount();
    expect(requestSignal?.aborted).toBe(true);
  });

  it("preserves real checklist availability errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 503 })));

    render(<InvestigationQualityAssessmentPanel investigationId={4} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("temporarily unavailable");
  });
});
