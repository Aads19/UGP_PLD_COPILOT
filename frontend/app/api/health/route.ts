import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET() {
  return NextResponse.json({
    ok: true,
    mode: "vercel-integrated",
    groqConfigured: Boolean(process.env.GROQ_API_KEY),
  });
}
