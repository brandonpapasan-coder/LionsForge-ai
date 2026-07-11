"use client";

import { FormEvent, useEffect, useState } from "react";

import type {
  MentorChatResponse,
  MentorConversation,
  MentorConversationDetail,
  MentorResponsePayload,
} from "@/lib/mentor";

type TranscriptItem = {
  id: string;
  role: "user" | "assistant";
  content: string;
  response: MentorResponsePayload | null;
};

export function MentorWorkspace() {
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [conversations, setConversations] = useState<MentorConversation[]>([]);
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshHistory() {
    const response = await fetch("/api/mentor/conversations", { cache: "no-store" });
    if (response.status === 401) {
      window.location.href = "/login";
      return;
    }
    if (response.ok) {
      setConversations((await response.json()) as MentorConversation[]);
    }
  }

  useEffect(() => {
    void refreshHistory();
  }, []);

  function startNewConversation() {
    setConversationId(null);
    setTranscript([]);
    setError(null);
  }

  async function openConversation(id: number) {
    setLoadingHistory(true);
    setError(null);
    try {
      const response = await fetch(`/api/mentor/conversations/${id}`, { cache: "no-store" });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) {
        setError("The conversation could not be opened.");
        return;
      }
      const detail = (await response.json()) as MentorConversationDetail;
      setConversationId(detail.id);
      setTranscript(
        detail.messages.map((message) => ({
          id: `persisted-${message.id}`,
          role: message.role,
          content: message.content,
          response: message.response_payload,
        })),
      );
    } catch {
      setError("Conversation history is unavailable.");
    } finally {
      setLoadingHistory(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const form = event.currentTarget;
    const data = new FormData(form);
    const message = String(data.get("message") ?? "").trim();
    if (!message) {
      setSubmitting(false);
      return;
    }

    const pendingUserId = `pending-user-${Date.now()}`;
    setTranscript((current) => [
      ...current,
      { id: pendingUserId, role: "user", content: message, response: null },
    ]);

    try {
      const response = await fetch("/api/mentor/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
          context: { goal: "Build evidence-based research and finance mastery" },
        }),
      });
      if (response.status === 401) {
        window.location.href = "/login";
        return;
      }
      if (!response.ok) {
        setError("The mentor could not respond. Please try again.");
        return;
      }
      const payload = (await response.json()) as MentorChatResponse;
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
      await refreshHistory();
    } catch {
      setError("The mentor service is unavailable.");
    } finally {
      setSubmitting(false);
    }
  }

  const latestResponse = [...transcript]
    .reverse()
    .find((item) => item.role === "assistant" && item.response)?.response;

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
              className={conversation.id === conversationId ? "active" : ""}
              key={conversation.id}
              onClick={() => void openConversation(conversation.id)}
            >
              <strong>{conversation.title}</strong>
              <span>{conversation.summary ?? "Mentor conversation"}</span>
            </button>
          )) : <p className="muted">Your saved conversations will appear here.</p>}
        </div>
      </aside>

      <section className="mentor-chat">
        <header>
          <div>
            <p className="eyebrow">AI MENTOR</p>
            <h1>Think through the evidence.</h1>
          </div>
          <span className="confidence-chip">{latestResponse?.confidence ?? "ready"}</span>
        </header>

        <div className="conversation-stream" aria-live="polite">
          {transcript.length === 0 ? (
            <div className="empty-conversation">
              <h2>Start a conversation</h2>
              <p>Try: “Help me challenge the assumptions in a company valuation.”</p>
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
          <textarea id="message" name="message" required maxLength={8000} placeholder="What decision, lesson, or research question are you working through?" />
          <button type="submit" disabled={submitting}>{submitting ? "Thinking..." : "Send question"}</button>
          {error ? <p role="alert" className="form-message">{error}</p> : null}
        </form>
      </section>

      <aside className="mentor-sidebar recommendations-panel">
        <p className="eyebrow">NEXT ACTIONS</p>
        {latestResponse?.recommendations.length ? latestResponse.recommendations.map((item) => (
          <article key={`${item.title}-${item.action_type}`}>
            <strong>{item.title}</strong>
            <p>{item.reason}</p>
          </article>
        )) : <p className="muted">Recommendations will appear after your first mentor response.</p>}
      </aside>
    </div>
  );
}
