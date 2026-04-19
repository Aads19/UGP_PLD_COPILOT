export type Citation = {
  doi: string;
  title: string;
  url?: string | null;
};

export type Source = {
  chunk_id: string;
  title: string;
  doi: string;
  snippet: string;
  score?: number | null;
};

export type ChatMessage = {
  id: string;
  role: string;
  content_markdown: string;
  route: string;
  citations: Citation[];
  sources: Source[];
  created_at: string;
};

export type ChatRequest = {
  conversation_id?: string | null;
  message: string;
};

export type ChatResponse = {
  conversation_id: string;
  message: ChatMessage;
};

export type ConversationSummary = {
  id: string;
  title: string;
  preview: string;
  created_at?: string;
  updated_at?: string;
};

export type ConversationDetail = {
  id: string;
  title: string;
  created_at?: string;
  updated_at?: string;
  messages: ChatMessage[];
};
