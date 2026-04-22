import ReactMarkdown from "react-markdown";

import { UiMessage } from "../lib/types";
import { SourcesCard } from "./sources-card";

type MessageBubbleProps = {
  message: UiMessage;
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
        <ReactMarkdown>{message.content}</ReactMarkdown>
      </div>

      {isAssistant ? <SourcesCard sources={message.sources} /> : null}
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
