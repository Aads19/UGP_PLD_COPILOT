import { ChatRequest, ChatResponse, ConversationMessage, ConversationSummary } from "./types";

const RAW_API_BASE = process.env.NEXT_PUBLIC_API_URL;
const API_BASE = RAW_API_BASE?.replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (!API_BASE) {
    throw new Error("Backend API is not configured. Set NEXT_PUBLIC_API_URL.");
  }

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

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function chat(payload: ChatRequest) {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function fetchConversations() {
  return request<ConversationSummary[]>("/api/conversations");
}

export function fetchConversation(id: string) {
  return request<ConversationMessage[]>(`/api/conversations/${id}`);
}

export function deleteConversation(id: string) {
  return request<{ deleted: boolean; conversation_id: string }>(`/api/conversations/${id}`, {
    method: "DELETE"
  });
}
