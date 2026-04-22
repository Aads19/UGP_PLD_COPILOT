import { ConversationSummary } from "../lib/types";

type ConversationSidebarProps = {
  conversations: ConversationSummary[];
  onSelect: (id: string) => Promise<void> | void;
};

export function ConversationSidebar({ conversations, onSelect }: ConversationSidebarProps) {
  return (
    <aside className="panel sidebar">
      <h2>Saved Chats</h2>
      <p className="muted">
        Anonymous conversation history is stored in the backend so you can reopen earlier threads.
      </p>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="conversation-item">
            <strong>No saved conversations yet</strong>
            <span className="muted">Your first answered prompt will appear here.</span>
          </div>
        ) : (
          conversations.map((conversation) => (
            <button
              className="conversation-item"
              key={conversation.conversation_id}
              onClick={() => void onSelect(conversation.conversation_id)}
            >
              <strong>{conversation.first_message || "Untitled conversation"}</strong>
              <span className="muted">{formatDate(conversation.created_at)}</span>
            </button>
          ))
        )}
      </div>
    </aside>
  );
}

function formatDate(value?: string) {
  if (!value) {
    return "Open this thread";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Open this thread";
  }
  return date.toLocaleDateString();
}
