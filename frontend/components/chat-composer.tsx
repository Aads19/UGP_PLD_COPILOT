"use client";

import { FormEvent, useEffect, useRef } from "react";

type ChatComposerProps = {
  value: string;
  onChange: (message: string) => void;
  onSend: (message: string) => Promise<void> | void;
  disabled?: boolean;
  focusSignal?: number;
};

export function ChatComposer({
  value,
  onChange,
  onSend,
  disabled = false,
  focusSignal = 0
}: ChatComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, [focusSignal]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = value.trim();
    if (!message || disabled) {
      return;
    }
    onChange("");
    await onSend(message);
  }

  return (
    <form onSubmit={handleSubmit}>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Ask a PLD or thin-film literature question..."
        disabled={disabled}
      />
      <div className="composer-actions">
        <span className="muted">Ask about growth conditions, evidence, characterization, or thin-film mechanisms.</span>
        <button className="button-primary" type="submit" disabled={disabled}>
          Send
        </button>
      </div>
    </form>
  );
}
