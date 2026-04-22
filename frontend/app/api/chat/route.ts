import { NextRequest, NextResponse } from "next/server";

import corpus from "../../../lib/corpus.json";

export const runtime = "nodejs";

type CorpusRow = {
  doi: string;
  title: string;
  text: string;
  tags: string[];
};

type ChatRequest = {
  conversation_id?: string | null;
  message: string;
};

const SMALL_TALK = /^(hi|hello|hey|thanks|thank you|how are you)\b/i;
const MODEL = process.env.GROQ_MODEL ?? "llama-3.1-8b-instant";

export async function POST(request: NextRequest) {
  const body = (await request.json()) as ChatRequest;
  const message = body.message?.trim();
  const conversationId = body.conversation_id || crypto.randomUUID();

  if (!message) {
    return NextResponse.json({ detail: "Message is required." }, { status: 400 });
  }

  if (SMALL_TALK.test(message)) {
    return NextResponse.json({
      conversation_id: conversationId,
      message: buildAssistantMessage({
        route: "chat",
        content_markdown:
          "This copilot is tuned for PLD and thin-film literature questions. Ask about growth conditions, synthesis, characterization, mechanisms, or evidence from the indexed corpus.",
        citations: [],
        sources: [],
      }),
    });
  }

  if (!process.env.GROQ_API_KEY) {
    return NextResponse.json({
      conversation_id: conversationId,
      message: buildAssistantMessage({
        route: "system",
        content_markdown:
          "The deployed chatbot is online, but `GROQ_API_KEY` is not configured yet. Add that environment variable in Vercel to enable live answer generation.",
        citations: [],
        sources: [],
      }),
    });
  }

  const sources = retrieveSources(message, corpus as CorpusRow[]);
  const citations = uniqueCitations(sources);

  let content = "I could not find strong enough evidence in the indexed corpus to answer that safely.";
  if (sources.length > 0) {
    try {
      content = await groqAnswer(message, sources);
    } catch {
      content =
        "I found relevant source material, but the model call failed before I could complete the synthesis. Please retry in a moment.";
    }
  }

  return NextResponse.json({
    conversation_id: conversationId,
    message: buildAssistantMessage({
      route: "database",
      content_markdown: content,
      citations,
      sources,
    }),
  });
}

function buildAssistantMessage({
  route,
  content_markdown,
  citations,
  sources,
}: {
  route: string;
  content_markdown: string;
  citations: Array<{ doi: string; title: string; url: string | null }>;
  sources: Array<{ chunk_id: string; title: string; doi: string; snippet: string; score: number }>;
}) {
  return {
    id: crypto.randomUUID(),
    role: "assistant",
    content_markdown,
    route,
    citations,
    sources,
    created_at: new Date().toISOString(),
  };
}

function retrieveSources(query: string, rows: CorpusRow[]) {
  const tokens = tokenize(query);
  const scored = rows
    .map((row, index) => {
      const title = row.title.toLowerCase();
      const text = row.text.toLowerCase();
      const tags = row.tags.join(" ").toLowerCase();
      let score = 0;
      for (const token of tokens) {
        if (title.includes(token)) score += 6;
        if (tags.includes(token)) score += 4;
        if (text.includes(token)) score += 1;
      }
      return {
        row,
        index,
        score,
      };
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 6);

  return scored.map((item) => ({
    chunk_id: `chunk-${item.index}`,
    title: item.row.title,
    doi: item.row.doi,
    snippet: item.row.text.length > 360 ? `${item.row.text.slice(0, 357).trim()}...` : item.row.text,
    score: item.score,
  }));
}

function uniqueCitations(
  sources: Array<{ chunk_id: string; title: string; doi: string; snippet: string; score: number }>
) {
  const seen = new Set<string>();
  return sources
    .filter((source) => {
      if (!source.doi || seen.has(source.doi)) {
        return false;
      }
      seen.add(source.doi);
      return true;
    })
    .map((source) => ({
      doi: source.doi,
      title: source.title,
      url: source.doi ? `https://doi.org/${source.doi}` : null,
    }));
}

async function groqAnswer(
  query: string,
  sources: Array<{ chunk_id: string; title: string; doi: string; snippet: string; score: number }>
) {
  const evidenceBlock = sources
    .map(
      (source, index) =>
        `Source ${index + 1}\nTitle: ${source.title}\nDOI: ${source.doi}\nEvidence: ${source.snippet}`
    )
    .join("\n\n");

  const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${process.env.GROQ_API_KEY}`,
    },
    body: JSON.stringify({
      model: MODEL,
      temperature: 0.2,
      messages: [
        {
          role: "system",
          content:
            "You are a PLD literature copilot. Answer only from the provided evidence. If the evidence is weak or partial, say so clearly. Use concise Markdown and include inline DOI citations like [DOI: ...].",
        },
        {
          role: "user",
          content: `Question:\n${query}\n\nEvidence:\n${evidenceBlock}`,
        },
      ],
    }),
  });

  if (!response.ok) {
    throw new Error("Groq request failed");
  }

  const data = (await response.json()) as {
    choices?: Array<{ message?: { content?: string } }>;
  };
  return (
    data.choices?.[0]?.message?.content?.trim() ??
    "The model returned an empty response even though relevant evidence was retrieved."
  );
}

function tokenize(input: string) {
  return Array.from(
    new Set(
      input
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, " ")
        .split(/\s+/)
        .filter((token) => token.length > 2)
    )
  );
}
