"use client";

import { ChatMessage, ConversationDetail, ConversationSummary } from "./types";

const STORAGE_KEY = "ugp-pld-copilot-conversations";

type StoredConversation = ConversationDetail;

function loadAll(): StoredConversation[] {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as StoredConversation[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveAll(conversations: StoredConversation[]) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
}

export function listStoredConversations(): ConversationSummary[] {
  return loadAll()
    .sort((a, b) => (b.updated_at ?? "").localeCompare(a.updated_at ?? ""))
    .map((conversation) => ({
      id: conversation.id,
      title: conversation.title,
      preview: conversation.messages[conversation.messages.length - 1]?.content_markdown.slice(0, 140) ?? "",
      created_at: conversation.created_at,
      updated_at: conversation.updated_at,
    }));
}

export function getStoredConversation(id: string): ConversationDetail | null {
  return loadAll().find((conversation) => conversation.id === id) ?? null;
}

export function saveStoredConversation(id: string, messages: ChatMessage[]): ConversationDetail {
  const conversations = loadAll();
  const now = new Date().toISOString();
  const existing = conversations.find((conversation) => conversation.id === id);
  const title = buildTitle(messages);

  const nextConversation: ConversationDetail = {
    id,
    title,
    created_at: existing?.created_at ?? now,
    updated_at: now,
    messages,
  };

  const nextList = [nextConversation, ...conversations.filter((conversation) => conversation.id !== id)];
  saveAll(nextList);
  return nextConversation;
}

function buildTitle(messages: ChatMessage[]) {
  const firstUserMessage = messages.find((message) => message.role === "user")?.content_markdown.trim() ?? "New conversation";
  return firstUserMessage.length > 80 ? `${firstUserMessage.slice(0, 77).trim()}...` : firstUserMessage;
}
