export type Source = {
  doi: string;
  title: string;
  chunk_idx: number;
};

export type ConversationMessage = {
  role: "user" | "assistant";
  content: string;
  sources: Source[];
  created_at: string;
};

export type UiMessage = ConversationMessage & {
  id: string;
};

export type ChatRequest = {
  conversation_id?: string | null;
  message: string;
};

export type ChatResponse = {
  answer: string;
  sources: Source[];
  conversation_id: string;
};

export type ConversationSummary = {
  conversation_id: string;
  first_message: string;
  created_at?: string;
};
