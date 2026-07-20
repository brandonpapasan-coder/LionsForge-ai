import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InvestigationSynthesisPanel } from "@/components/investigation-synthesis-panel";

describe("InvestigationSynthesisPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("aborts both initial requests when the panel unmounts", () => {
    const requestSignals: AbortSignal[] = [];
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      requestSignals.push(init?.signal as AbortSignal);
      return new Promise<Response>(() => undefined);
    }));

    const { unmount } = render(<InvestigationSynthesisPanel investigationId={4} />);

    expect(requestSignals).toHaveLength(2);
    expect(requestSignals[0]).toBe(requestSignals[1]);
    expect(requestSignals.every((signal) => signal.aborted === false)).toBe(true);

    unmount();

    expect(requestSignals.every((signal) => signal.aborted === true)).toBe(true);
  });

  it("preserves real synthesis availability errors", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(new Response("{}", { status: 503 }))
      .mockResolvedValueOnce(new Response("{}", { status: 503 })));

    render(<InvestigationSynthesisPanel investigationId={4} />);

    expect(await screen.findByRole("alert")).toHaveTextContent("temporarily unavailable");
  });
});
