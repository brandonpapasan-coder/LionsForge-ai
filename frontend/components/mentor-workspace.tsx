"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import type {
  MentorChatResponse,
  MentorConversation,
  MentorConversationDetail,
  MentorResponsePayload,
} from "@/lib/mentor";

type MentorWorkspaceProps = {
  researchProjectId: string | null;
  researchSessionId: string | null;
};

type TranscriptItem = {
  id: string;
  role: "user" | "assistant";
  content: string;
  response: MentorResponsePayload | null;
};

function isAbortError(error: unknown) {
  return error instanceof DOMException && error.name === "AbortError";
}

export function MentorWorkspace({ researchProjectId, researchSessionId }: MentorWorkspaceProps) {
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [conversations, setConversations] = useState<MentorConversation[]>([]);
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const historyRequest = useRef<AbortController | null>(null);
  const conversationRequest = useRef<AbortController | null>(null);
  const chatRequest = useRef<AbortController | null>(null);
  const contextKey = `${researchProjectId ?? "none"}:${researchSessionId ?? "none"}`;
  const previousContextKey = useRef(contextKey);

  const activeContext = useMemo(() => ({
    goal: "Build evidence-based research and finance mastery",
    ...(researchProjectId ? { research_project_id: researchProjectId } : {}),
    ...(researchSessionId ? { research_session_id: researchSessionId } : {}),
  }), [researchProjectId, researchSessionId]);

  async function refreshHistory() {
    historyRequest.current?.abort();
    const controller = new AbortController();
    historyRequest.current = controller;

    try {
      const response = await fetch("/api/mentor/conversations", {
        cache: "no-store",
        signal: controller.signal,
      });
      if (controller.signal.aborted || historyRequest.current !== controller) return;
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (response.ok) {
        const payload = (await response.json()) as MentorConversation[];
        if (!controller.signal.aborted && historyRequest.current === controller) {
          setConversations(payload);
        }
      }
    } catch (requestError) {
      if (!isAbortError(requestError) && !controller.signal.aborted) {
        // History refresh failures remain non-blocking so the active conversation stays usable.
      }
    } finally {
      if (historyRequest.current === controller) historyRequest.current = null;
    }
  }

  useEffect(() => {
    void refreshHistory();
    return () => {
      historyRequest.current?.abort();
      conversationRequest.current?.abort();
      chatRequest.current?.abort();
      historyRequest.current = null;
      conversationRequest.current = null;
      chatRequest.current = null;
    };
  }, []);

  useEffect(() => {
    if (previousContextKey.current === contextKey) return;
    previousContextKey.current = contextKey;

    conversationRequest.current?.abort();
    chatRequest.current?.abort();
    conversationRequest.current = null;
    chatRequest.current = null;
    setLoadingHistory(false);
    setSubmitting(false);
    setConversationId(null);
    setTranscript([]);
    setError(null);
  }, [contextKey]);

  function startNewConversation() {
    conversationRequest.current?.abort();
    chatRequest.current?.abort();
    conversationRequest.current = null;
    chatRequest.current = null;
    setLoadingHistory(false);
    setSubmitting(false);
    setConversationId(null);
    setTranscript([]);
    setError(null);
  }

  async function openConversation(id: number) {
    conversationRequest.current?.abort();
    chatRequest.current?.abort();
    chatRequest.current = null;
    setSubmitting(false);

    const controller = new AbortController();
    conversationRequest.current = controller;
    setLoadingHistory(true);
    setError(null);

    try {
      const response = await fetch(`/api/mentor/conversations/${id}`, {
        cache: "no-store",
        signal: controller.signal,
      });
      if (controller.signal.aborted || conversationRequest.current !== controller) return;
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) {
        setError("The conversation could not be opened.");
        return;
      }
      const detail = (await response.json()) as MentorConversationDetail;
      if (controller.signal.aborted || conversationRequest.current !== controller) return;
      setConversationId(detail.id);
      setTranscript(detail.messages.map((message) => ({
        id: `persisted-${message.id}`,
        role: message.role,
        content: message.content,
        response: message.response_payload,
      })));
    } catch (requestError) {
      if (!isAbortError(requestError) && !controller.signal.aborted && conversationRequest.current === controller) {
        setError("Conversation history is unavailable.");
      }
    } finally {
      if (conversationRequest.current === controller) {
        conversationRequest.current = null;
        setLoadingHistory(false);
      }
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const message = String(data.get("message") ?? "").trim();
    if (!message) return;

    chatRequest.current?.abort();
    conversationRequest.current?.abort();
    conversationRequest.current = null;
    setLoadingHistory(false);

    const controller = new AbortController();
    chatRequest.current = controller;
    setSubmitting(true);
    setError(null);
    setTranscript((current) => [
      ...current,
      { id: `user-${Date.now()}`, role: "user", content: message, response: null },
    ]);

    try {
      const response = await fetch("/api/mentor/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
          context: activeContext,
        }),
        signal: controller.signal,
      });
      if (controller.signal.aborted || chatRequest.current !== controller) return;
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) {
        setError("The mentor could not respond. Please try again.");
        return;
      }
      const payload = (await response.json()) as MentorChatResponse;
      if (controller.signal.aborted || chatRequest.current !== controller) return;
      setConversationId(payload.conversation_id);
      setTranscript((current) => [
        ...current,
        {
          id: `assistant-${payload.message_id}`,
          role: "assistant",
          content: payload.answer,
          response: payload,
        },
      ]);
      form.reset();
      void refreshHistory();
    } catch (requestError) {
      if (!isAbortError(requestError) && !controller.signal.aborted && chatRequest.current === controller) {
        setError("The mentor service is unavailable.");
      }
    } finally {
      if (chatRequest.current === controller) {
        chatRequest.current = null;
        setSubmitting(false);
      }
    }
  }

  const latest = [...transcript].reverse().find((item) => item.role === "assistant" && item.response)?.response;
  const hasResearchContext = Boolean(researchProjectId || researchSessionId);

  return (
    <div className="mentor-grid">
      <aside className="mentor-sidebar history-panel">
        <div className="history-heading">
          <div>
            <p className="eyebrow">CONVERSATIONS</p>
            <h2>Mentor history</h2>
          </div>
          <button type="button" onClick={startNewConversation}>New</button>
        </div>
        <div className="history-list" aria-busy={loadingHistory}>
          {conversations.length ? conversations.map((conversation) => (
            <button
              type="button"
              key={conversation.id}
              className={conversation.id === conversationId ? "active" : ""}
              onClick={() => void openConversation(conversation.id)}
            >
              <strong>{conversation.title}</strong>
              <span>{conversation.summary ?? "Mentor conversation"}</span>
            </button>
          )) : <p className="muted">Saved conversations will appear here.</p>}
        </div>
      </aside>

      <section className="mentor-chat">
        <header>
          <div>
            <p className="eyebrow">AI MENTOR</p>
            <h1>Think through the evidence.</h1>
          </div>
          <span className="confidence-chip">{latest?.confidence ?? "ready"}</span>
        </header>

        <div className="conversation-stream" aria-live="polite">
          {transcript.length === 0 ? (
            <div className="empty-conversation">
              <h2>{hasResearchContext ? "Review the active research" : "Start a conversation"}</h2>
              <p>{hasResearchContext
                ? "Ask the mentor to challenge assumptions or identify missing evidence."
                : "Try: “Help me challenge the assumptions in a company valuation.”"}</p>
            </div>
          ) : transcript.map((item) => item.role === "user" ? (
            <article className="user-message" key={item.id}>
              <span>You</span>
              <p>{item.content}</p>
            </article>
          ) : (
            <article className="mentor-response" key={item.id}>
              <div className="response-meta">
                <span>{item.response?.persona ?? "LionsForge Mentor"}</span>
                <span>{item.response?.intent ?? "mentor"}</span>
              </div>
              <p>{item.content}</p>
              {item.response ? (
                <details>
                  <summary>View evidence and reasoning</summary>
                  <h3>Evidence</h3>
                  <ul>{item.response.evidence.map((evidence) => <li key={`${evidence.label}-${evidence.detail}`}><strong>{evidence.label}:</strong> {evidence.detail}</li>)}</ul>
                  <h3>Reasoning</h3>
                  <ul>{item.response.reasoning.map((reason) => <li key={reason}>{reason}</li>)}</ul>
                  <h3>Confidence</h3>
                  <p>{item.response.confidence_reason}</p>
                </details>
              ) : null}
            </article>
          ))}
        </div>

        <form className="mentor-composer" onSubmit={handleSubmit}>
          <label htmlFor="message">Ask the mentor</label>
          <textarea
            id="message"
            name="message"
            required
            maxLength={8000}
            placeholder={hasResearchContext
              ? "What should the mentor challenge or validate in this research?"
              : "What decision, lesson, or research question are you working through?"}
          />
          <button type="submit" disabled={submitting}>{submitting ? "Thinking..." : "Send question"}</button>
          {error ? <p role="alert" className="form-message">{error}</p> : null}
        </form>
      </section>

      <aside className="mentor-sidebar recommendations-panel">
        <p className="eyebrow">NEXT ACTIONS</p>
        {latest?.recommendations.length ? latest.recommendations.map((item) => (
          <article key={`${item.title}-${item.action_type}`}>
            <strong>{item.title}</strong>
            <p>{item.reason}</p>
          </article>
        )) : <p className="muted">Recommendations will appear after the first mentor response.</p>}
      </aside>
    </div>
  );
}
