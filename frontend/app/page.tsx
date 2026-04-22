"use client";

import { useEffect, useState } from "react";

import { ChatComposer } from "../components/chat-composer";
import { ChatWindow } from "../components/chat-window";
import { ConversationSidebar } from "../components/conversation-sidebar";
import { chat, fetchConversation, fetchConversations } from "../lib/api";
import { ConversationMessage, ConversationSummary, UiMessage } from "../lib/types";

const EXAMPLES = [
  "What PLD growth parameters most strongly influence thin-film crystallinity?",
  "Summarize synthesis and characterization evidence for PZT thin films on Pt substrates.",
  "Which retrieved papers discuss pyrolysis temperature effects on film texture?"
];

export default function HomePage() {
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [focusSignal, setFocusSignal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void refreshConversations();
  }, []);

  async function refreshConversations() {
    try {
      const items = await fetchConversations();
      setConversations(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load saved conversations.");
    }
  }

  async function handleSend(message: string) {
    setLoading(true);
    setError(null);

    const optimisticUserMessage = createUiMessage({
      role: "user",
      content: message,
      sources: [],
      created_at: new Date().toISOString()
    });
    const nextMessages = [...messages, optimisticUserMessage];
    setMessages(nextMessages);

    try {
      const response = await chat({
        conversation_id: conversationId,
        message
      });
      const assistantMessage = createUiMessage({
        role: "assistant",
        content: response.answer,
        sources: response.sources,
        created_at: new Date().toISOString()
      });
      setConversationId(response.conversation_id);
      setMessages([...nextMessages, assistantMessage]);
      await refreshConversations();
    } catch (err) {
      const fallback = "The research server is temporarily unavailable. Please try again in a moment.";
      const assistantMessage = createUiMessage({
        role: "assistant",
        content: fallback,
        sources: [],
        created_at: new Date().toISOString()
      });
      setMessages([...nextMessages, assistantMessage]);
      setError(err instanceof Error ? err.message : fallback);
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadConversation(id: string) {
    setLoading(true);
    setError(null);
    try {
      const conversation = await fetchConversation(id);
      setConversationId(id);
      setMessages(conversation.map(createUiMessage));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load that conversation.");
    } finally {
      setLoading(false);
    }
  }

  function handlePickExample(question: string) {
    setDraft(question);
    setFocusSignal((current) => current + 1);
  }

  return (
    <main>
      <section className="shell page-header">
        <h1 className="page-title">UGP PLD Copilot</h1>
      </section>

      <section className="shell app-grid" id="chat">
        <ConversationSidebar conversations={conversations} onSelect={handleLoadConversation} />

        <div className="panel chat-panel">
          <div className="chat-header">
            <h2>Chatbot Workspace</h2>
            <p className="muted">
              Ask about PVD synthesis, thin-film processing, characterization, or evidence from the indexed
              literature corpus.
            </p>
            {error ? <div className="error-banner">{error}</div> : null}
          </div>

          <ChatWindow
            messages={messages}
            loading={loading}
            examples={EXAMPLES}
            onPickExample={handlePickExample}
          />

          <div className="composer">
            <ChatComposer
              value={draft}
              onChange={setDraft}
              onSend={handleSend}
              disabled={loading}
              focusSignal={focusSignal}
            />
          </div>
        </div>
      </section>
    </main>
  );
}

function createUiMessage(message: ConversationMessage): UiMessage {
  return {
    ...message,
    id: `${message.role}-${message.created_at}-${Math.random().toString(36).slice(2, 8)}`
  };
}
