import ReactMarkdown from "react-markdown";

import { UiMessage } from "../lib/types";
import { MessageBubble } from "./message-bubble";
import { SuggestedQuestions } from "./suggested-questions";

type ChatWindowProps = {
  messages: UiMessage[];
  loading: boolean;
  examples: string[];
  onPickExample: (question: string) => void;
};

export function ChatWindow({ messages, loading, examples, onPickExample }: ChatWindowProps) {
  return (
    <div className="chat-scroll">
      {messages.length === 0 ? (
        <div className="empty-state">
          <div>
            <h3>Start with a literature-grounded PVD question</h3>
            <p className="muted">
              Ask about deposition conditions, characterization methods, thin-film performance, or
              evidence from the indexed research corpus.
            </p>
            <SuggestedQuestions questions={examples} onSelect={onPickExample} />
          </div>
        </div>
      ) : (
        messages.map((message) => <MessageBubble key={message.id} message={message} />)
      )}

      {loading ? (
        <div className="bubble assistant">
          <div className="bubble-header">
            <strong>UGP PLD Copilot</strong>
            <span className="muted">Thinking...</span>
          </div>
          <div className="bubble-body">
            <ReactMarkdown>
              {`Routing the query, retrieving literature evidence, reranking sources, and preparing a grounded answer...`}
            </ReactMarkdown>
          </div>
        </div>
      ) : null}
    </div>
  );
}
