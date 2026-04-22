"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

import { ChatComposer } from "../components/chat-composer";
import { ConversationSidebar } from "../components/conversation-sidebar";
import { MessageBubble } from "../components/message-bubble";
import { chat } from "../lib/api";
import { getStoredConversation, listStoredConversations, saveStoredConversation } from "../lib/storage";
import { ChatMessage, ConversationSummary } from "../lib/types";

const EXAMPLES = [
  "What PLD growth parameters most strongly influence thin-film crystallinity?",
  "Summarize synthesis and characterization evidence for PZT thin films on Pt substrates.",
  "Which retrieved papers discuss pyrolysis temperature effects on film texture?"
];

export default function HomePage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setConversations(listStoredConversations());
  }, []);

  async function handleSend(message: string) {
    setLoading(true);
    setError(null);

    const activeConversationId = conversationId ?? crypto.randomUUID();
    const optimisticUserMessage: ChatMessage = {
      id: `local-user-${Date.now()}`,
      role: "user",
      content_markdown: message,
      route: "user",
      citations: [],
      sources: [],
      created_at: new Date().toISOString()
    };
    const nextMessages = [...messages, optimisticUserMessage];
    setConversationId(activeConversationId);
    setMessages(nextMessages);
    saveStoredConversation(activeConversationId, nextMessages);
    setConversations(listStoredConversations());

    try {
      const response = await chat({
        conversation_id: activeConversationId,
        message
      });
      const resolvedConversationId = response.conversation_id || activeConversationId;
      const finalMessages = [...nextMessages, response.message];
      setConversationId(resolvedConversationId);
      setMessages(finalMessages);
      saveStoredConversation(resolvedConversationId, finalMessages);
      setConversations(listStoredConversations());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reach the backend right now.");
    } finally {
      setLoading(false);
    }
  }

  async function handleLoadConversation(id: string) {
    setLoading(true);
    setError(null);
    try {
      const conversation = getStoredConversation(id);
      if (!conversation) {
        throw new Error("Unable to load that conversation.");
      }
      setConversationId(conversation.id);
      setMessages(conversation.messages);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load that conversation.");
    } finally {
      setLoading(false);
    }
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
              Ask about PLD synthesis, thin-film processing, characterization, or evidence from the indexed
              corpus. Answers include sources when the retrieval pipeline finds relevant support.
            </p>
          </div>

          <div className="chat-scroll">
            {error ? <div className="error-banner">{error}</div> : null}

            {messages.length === 0 ? (
              <div className="empty-state">
                <div>
                  <h3>Start with a literature-grounded PLD question</h3>
                  <p className="muted">
                    The first release is optimized for source-backed answers and anonymous saved conversations.
                  </p>
                  <div className="example-grid">
                    {EXAMPLES.map((example) => (
                      <button key={example} onClick={() => void handleSend(example)}>
                        {example}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              messages.map((message) => <MessageBubble key={message.id} message={message} />)
            )}

            {loading ? (
              <div className="bubble assistant">
                <div className="bubble-header">
                  <strong>UGP PLD Copilot</strong>
                  <span className="muted">Thinking</span>
                </div>
                <div className="bubble-body">
                  <ReactMarkdown>
                    {`Reviewing the indexed corpus, grading evidence, and preparing a source-backed response...`}
                  </ReactMarkdown>
                </div>
              </div>
            ) : null}
          </div>

          <div className="composer">
            <ChatComposer onSend={handleSend} disabled={loading} />
          </div>
        </div>
      </section>
    </main>
  );
}
