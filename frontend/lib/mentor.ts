export type EvidenceItem = {
  label: string;
  detail: string;
  source_type: string;
};

export type MentorRecommendation = {
  title: string;
  reason: string;
  action_type: string;
  action_target: string | null;
};

export type MentorResponsePayload = {
  intent: string;
  persona: string;
  answer: string;
  evidence: EvidenceItem[];
  reasoning: string[];
  assumptions: string[];
  confidence: string;
  confidence_reason: string;
  alternative_viewpoints: string[];
  recommendations: MentorRecommendation[];
};

export type MentorChatResponse = MentorResponsePayload & {
  conversation_id: number;
  message_id: number;
  created_at: string;
};

export type MentorConversation = {
  id: number;
  title: string;
  summary: string | null;
  active_context: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type MentorMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  intent: string | null;
  persona: string | null;
  response_payload: MentorResponsePayload | null;
  created_at: string;
};

export type MentorConversationDetail = MentorConversation & {
  messages: MentorMessage[];
};
