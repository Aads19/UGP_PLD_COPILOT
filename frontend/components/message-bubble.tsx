import ReactMarkdown from "react-markdown";

import { ChatMessage } from "../lib/types";

type MessageBubbleProps = {
  message: ChatMessage;
};

export function MessageBubble({ message }: MessageBubbleProps) {
  const isAssistant = message.role === "assistant";

  return (
    <article className={`bubble ${isAssistant ? "assistant" : "user"}`}>
      <div className="bubble-header">
        <strong>{isAssistant ? "UGP PLD Copilot" : "You"}</strong>
        <span>{formatDate(message.created_at)}</span>
      </div>

      <div className="bubble-body">
        <ReactMarkdown>{message.content_markdown}</ReactMarkdown>
      </div>

      {isAssistant && message.citations.length > 0 ? (
        <div className="citations">
          {message.citations.map((citation) => (
            <a
              className="citation-link"
              href={citation.url ?? "#"}
              key={`${message.id}-${citation.doi}`}
              rel="noreferrer"
              target="_blank"
            >
              <strong>{citation.title || citation.doi}</strong>
              <span className="muted">{citation.doi}</span>
            </a>
          ))}
        </div>
      ) : null}

      {isAssistant && message.sources.length > 0 ? (
        <details className="details">
          <summary>View retrieved evidence</summary>
          <div className="source-list">
            {message.sources.map((source) => (
              <div className="source-card" key={`${message.id}-${source.chunk_id}`}>
                <strong>{source.title || "Untitled source"}</strong>
                <div className="muted">{source.doi}</div>
                <p>{source.snippet}</p>
              </div>
            ))}
          </div>
        </details>
      ) : null}
    </article>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleString();
}
