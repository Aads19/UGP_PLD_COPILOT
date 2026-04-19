"use client";

import { FormEvent, useState } from "react";

type ChatComposerProps = {
  onSend: (message: string) => Promise<void> | void;
  disabled?: boolean;
};

export function ChatComposer({ onSend, disabled = false }: ChatComposerProps) {
  const [value, setValue] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = value.trim();
    if (!message || disabled) {
      return;
    }
    setValue("");
    await onSend(message);
  }

  return (
    <form onSubmit={handleSubmit}>
      <textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Ask a PLD or thin-film literature question..."
        disabled={disabled}
      />
      <div className="composer-actions">
        <span className="muted">Sources appear beneath each assistant answer when evidence is available.</span>
        <button className="button-primary" type="submit" disabled={disabled}>
          Send
        </button>
      </div>
    </form>
  );
}
