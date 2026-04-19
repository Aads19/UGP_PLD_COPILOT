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
              key={conversation.id}
              onClick={() => void onSelect(conversation.id)}
            >
              <strong>{conversation.title}</strong>
              <span className="muted">{conversation.preview || "Open this thread"}</span>
            </button>
          ))
        )}
      </div>
    </aside>
  );
}
