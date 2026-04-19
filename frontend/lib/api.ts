import { ChatRequest, ChatResponse, ConversationDetail, ConversationSummary } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const fallback = "Request failed.";
    try {
      const body = (await response.json()) as { detail?: string };
      throw new Error(body.detail ?? fallback);
    } catch {
      throw new Error(fallback);
    }
  }

  return (await response.json()) as T;
}

export function chat(payload: ChatRequest) {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function fetchConversations() {
  return request<ConversationSummary[]>("/conversations");
}

export function fetchConversation(id: string) {
  return request<ConversationDetail>(`/conversations/${id}`);
}
