"use client";

import { FormEvent, useState } from "react";

import type { MentorChatResponse } from "@/lib/mentor";

type MentorWorkspaceProps = {
  researchProjectId: string | null;
  researchSessionId: string | null;
};

export function MentorWorkspace({ researchProjectId, researchSessionId }: MentorWorkspaceProps) {
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [responses, setResponses] = useState<MentorChatResponse[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeContext = {
    goal: "Build evidence-based research and finance mastery",
    ...(researchProjectId ? { research_project_id: researchProjectId } : {}),
    ...(researchSessionId ? { research_session_id: researchSessionId } : {}),
  };

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

    try {
      const response = await fetch("/api/mentor/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
          context: activeContext,
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
      setResponses((current) => [...current, payload]);
      form.reset();
    } catch {
      setError("The mentor service is unavailable.");
    } finally {
      setSubmitting(false);
    }
  }

  const latest = responses.at(-1);
  const hasResearchContext = Boolean(researchProjectId || researchSessionId);

  return (
    <div className="mentor-grid">
      <aside className="mentor-sidebar">
        <p className="eyebrow">MENTOR CONTEXT</p>
        <h2>{hasResearchContext ? "Research context active." : "Build stronger judgment."}</h2>
        <p className="muted">
          {hasResearchContext
            ? "Your active research identifiers will be preserved with this mentor conversation."
            : "Ask about finance, research, economics, portfolios, or your learning path."}
        </p>
        <div className="context-card">
          <span>Active goal</span>
          <strong>Evidence-based mastery</strong>
        </div>
        {researchProjectId ? (
          <div className="context-card">
            <span>Research project</span>
            <strong>Project #{researchProjectId}</strong>
          </div>
        ) : null}
        {researchSessionId ? (
          <div className="context-card">
            <span>Research session</span>
            <strong>Session #{researchSessionId}</strong>
          </div>
        ) : null}
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
          {responses.length === 0 ? (
            <div className="empty-conversation">
              <h2>{hasResearchContext ? "Review the active research" : "Start a conversation"}</h2>
              <p>
                {hasResearchContext
                  ? "Ask the mentor to challenge assumptions, identify missing evidence, or recommend the next research step."
                  : "Try: “Help me challenge the assumptions in a company valuation.”"}
              </p>
            </div>
          ) : (
            responses.map((response) => (
              <article className="mentor-response" key={response.message_id}>
                <div className="response-meta">
                  <span>{response.persona}</span>
                  <span>{response.intent}</span>
                </div>
                <p>{response.answer}</p>
                <details>
                  <summary>View evidence and reasoning</summary>
                  <h3>Evidence</h3>
                  <ul>{response.evidence.map((item) => <li key={`${item.label}-${item.detail}`}><strong>{item.label}:</strong> {item.detail}</li>)}</ul>
                  <h3>Reasoning</h3>
                  <ul>{response.reasoning.map((item) => <li key={item}>{item}</li>)}</ul>
                  <h3>Confidence</h3>
                  <p>{response.confidence_reason}</p>
                </details>
              </article>
            ))
          )}
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
        )) : <p className="muted">Recommendations will appear after your first mentor response.</p>}
      </aside>
    </div>
  );
}
