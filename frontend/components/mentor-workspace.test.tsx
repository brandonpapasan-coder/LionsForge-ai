import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { MentorWorkspace } from "@/components/mentor-workspace";
import type { MentorConversation, MentorConversationDetail } from "@/lib/mentor";

const conversations: MentorConversation[] = [
  {
    id: 1,
    title: "Evidence review",
    summary: "Review source quality.",
    active_context: {},
    created_at: "2026-07-15T12:00:00Z",
    updated_at: "2026-07-15T12:00:00Z",
  },
  {
    id: 2,
    title: "Assumption challenge",
    summary: "Challenge the working thesis.",
    active_context: {},
    created_at: "2026-07-15T12:00:00Z",
    updated_at: "2026-07-15T12:00:00Z",
  },
];

function detail(id: number, content: string): MentorConversationDetail {
  const conversation = conversations.find((item) => item.id === id)!;
  return {
    ...conversation,
    messages: [
      {
        id: id * 10,
        role: "assistant",
        content,
        intent: "mentor",
        persona: "Research Mentor",
        response_payload: null,
        created_at: "2026-07-15T12:00:00Z",
      },
    ],
  };
}

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

describe("MentorWorkspace request lifecycle", () => {
  it("keeps the newest selected conversation when an older request resolves late", async () => {
    const staleResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let staleSignal: AbortSignal | undefined;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/mentor/conversations") return response(conversations);
      if (url === "/api/mentor/conversations/1") {
        staleSignal = init?.signal ?? undefined;
        return staleResponse.promise;
      }
      if (url === "/api/mentor/conversations/2") return response(detail(2, "Current assumption analysis"));
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<MentorWorkspace researchProjectId={null} researchSessionId={null} />);
    fireEvent.click(await screen.findByRole("button", { name: /Evidence review/i }));
    fireEvent.click(screen.getByRole("button", { name: /Assumption challenge/i }));

    expect(await screen.findByText("Current assumption analysis")).toBeInTheDocument();
    expect(staleSignal?.aborted).toBe(true);

    staleResponse.resolve(await response(detail(1, "Stale evidence analysis")));
    await waitFor(() => expect(screen.queryByText("Stale evidence analysis")).not.toBeInTheDocument());
    expect(screen.getByText("Current assumption analysis")).toBeInTheDocument();
  });

  it("aborts and clears an active mentor request when research context changes", async () => {
    const chatResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let chatSignal: AbortSignal | undefined;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/mentor/conversations") return response(conversations);
      if (url === "/api/mentor/chat") {
        chatSignal = init?.signal ?? undefined;
        return chatResponse.promise;
      }
      return response(null, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    const { rerender } = render(<MentorWorkspace researchProjectId="7" researchSessionId="70" />);
    await screen.findByRole("button", { name: /Evidence review/i });

    fireEvent.change(screen.getByRole("textbox", { name: "Ask the mentor" }), {
      target: { value: "Challenge this project's evidence." },
    });
    fireEvent.submit(screen.getByRole("textbox", { name: "Ask the mentor" }).closest("form")!);

    expect(await screen.findByText("Challenge this project's evidence.")).toBeInTheDocument();
    await waitFor(() => expect(chatSignal).toBeDefined());

    rerender(<MentorWorkspace researchProjectId="8" researchSessionId="80" />);

    expect(chatSignal?.aborted).toBe(true);
    expect(screen.queryByText("Challenge this project's evidence.")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Review the active research" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send question" })).toBeEnabled();

    chatResponse.resolve(await response(null, 500));
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
  });

  it("aborts the initial history request when unmounted", async () => {
    const historyResponse = deferred<Awaited<ReturnType<typeof response>>>();
    let historySignal: AbortSignal | undefined;
    const fetchMock = vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      historySignal = init?.signal ?? undefined;
      return historyResponse.promise;
    });
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<MentorWorkspace researchProjectId={null} researchSessionId={null} />);
    await waitFor(() => expect(historySignal).toBeDefined());
    unmount();

    expect(historySignal?.aborted).toBe(true);
  });
});
