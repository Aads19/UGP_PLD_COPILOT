# UGP PLD Copilot

UGP PLD Copilot is now structured as a deployable research chatbot for pulsed laser deposition literature workflows. The repository keeps the existing `pld_copilot` agentic RAG package, adds a `FastAPI` backend for chat and conversation APIs, and includes a `Next.js` frontend for a public chatbot-style interface.

The project now supports two deployment modes:

- `frontend/` can run as a self-contained Vercel deployment with integrated `/api/chat` and `/api/health` routes backed by Groq plus the bundled CSV corpus.
- `backend/` can still run as the full FastAPI service when you want the original Python pipeline, Chroma persistence, and Postgres-backed conversation storage.

## Architecture

- `pld_copilot/`: existing PLD agent pipeline, retrieval, grading, synthesis, critique, and formatting logic
- `backend/`: FastAPI service, database persistence, API routes, and Docker deployment setup
- `frontend/`: Next.js chatbot UI for public/demo access
- `render.yaml`: starter Render deployment manifest for the backend

The backend wraps the current pipeline instead of replacing it. The frontend renders answer markdown, DOI-linked citations, and expandable source evidence. In the Vercel-integrated mode, the same UI talks to colocated Next.js API routes instead of an external backend service.

## Features

- Public chatbot UI focused on PLD and thin-film literature questions
- Source-grounded answers with DOI links
- Expandable retrieved evidence snippets beneath answers
- Anonymous saved conversations
- Health endpoint for deployment checks
- Docker-ready backend deployment for Render or Railway
- Self-contained Vercel deployment path for a live demo without separate backend hosting

## Local Development

### 1. Backend

Create a Python environment and install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

Copy the backend environment template:

```powershell
Copy-Item .\backend\.env.example .\backend\.env
```

Set the required values in `backend/.env`:

- `GROQ_API_KEY`
- `DATABASE_URL`
- `CHROMA_PERSIST_DIRECTORY`
- `CHROMA_COLLECTION_NAME`
- model names and optional router overrides

Run the backend:

```powershell
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend

Install dependencies:

```powershell
cd frontend
npm install
```

Copy the frontend environment template:

```powershell
Copy-Item .\.env.example .\.env.local
```

Set:

- `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api` for split frontend/backend development
- or leave it unset to use the colocated `/api` routes in the Vercel-integrated mode
- `GROQ_API_KEY` if you want the integrated frontend API routes to generate live answers locally

Run the frontend:

```powershell
npm run dev
```

Open `http://localhost:3000`.

## API Overview

### `POST /api/chat`

Request:

```json
{
  "conversation_id": null,
  "message": "What PLD growth parameters influence crystallinity?"
}
```

Response includes:

- `conversation_id`
- assistant `message`
- `citations`
- `sources`
- route label

### `GET /api/conversations`

Returns saved anonymous conversation summaries.

### `GET /api/conversations/{id}`

Returns the full conversation history for one thread.

### `GET /api/health`

Reports API readiness, DB connectivity, Groq config presence, and Chroma retriever status.

## Chroma Setup

For the full Python backend, use your current Chroma artifacts as the source of truth instead of rebuilding embeddings during deploy.

Recommended layout:

- place the Chroma persistence bundle in a folder mounted or copied to the backend runtime
- set `CHROMA_PERSIST_DIRECTORY` to that folder
- set `CHROMA_COLLECTION_NAME` to the existing collection name in your Chroma database

The repository intentionally does not commit the Chroma binary store because the SQLite bundle exceeds normal GitHub file-size limits. Mount it on the deployment host and point `CHROMA_PERSIST_DIRECTORY` at that mounted folder.

If you deploy only the Vercel-integrated frontend, the app uses the bundled CSV corpus for lightweight retrieval and does not require Chroma to be mounted.

## Deployment

### Frontend on Vercel

Deploy the `frontend/` app from GitHub or with the Vercel CLI. The frontend can run online by itself without the FastAPI backend.

Environment variable:

- `GROQ_API_KEY`
- optionally `GROQ_MODEL`
- optionally `NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain/api` if you want the deployed UI to talk to the separate FastAPI backend instead of the built-in `/api` routes

### Backend on Render or Railway

Deploy using `backend/Dockerfile`.

Required environment variables:

- `GROQ_API_KEY`
- `LLM_BASE_URL`
- `LLM_ROUTER_MODEL`
- `LLM_REWRITE_MODEL`
- `LLM_GRADER_MODEL`
- `LLM_SYNTHESIS_MODEL`
- `LLM_CRITIC_MODEL`
- `LLM_FORMATTER_MODEL`
- `CHROMA_PERSIST_DIRECTORY`
- `CHROMA_COLLECTION_NAME`
- `DATABASE_URL`
- `API_RATE_LIMIT`
- `ALLOWED_ORIGINS`

For Render, `render.yaml` provides a starting point. Update the frontend domain and storage path before using it.

## Security Notes

- Rotate any personal access token or Hugging Face token that has ever been pasted into notebooks, chat, or committed files.
- Keep all secrets in environment variables only.
- Do not commit `.env` files.

## Troubleshooting

### Backend returns 503

Check:

- `GROQ_API_KEY`
- model names
- outbound network access from your host
- `CHROMA_PERSIST_DIRECTORY`

### Health endpoint says Chroma is unavailable

Check:

- `RETRIEVAL_ENABLED=true`
- correct Chroma path
- correct collection name
- `chromadb` installed in the backend environment

### No saved conversations appear

Check:

- `DATABASE_URL`
- database permissions
- backend startup logs for table creation issues

## Legacy CLI

The original CLI entrypoint still exists in [main.py](/C:/UGP%20-%20SHIKHA%20MISRA/main.py) for ingestion and command-line experiments with the underlying pipeline.
