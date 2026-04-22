# UGP PLD Copilot

## Project Overview
UGP PLD Copilot is an undergraduate research project that turns a categorized corpus of Physical Vapor Deposition (PVD) and Pulsed Laser Deposition (PLD) literature into a domain-specific AI assistant. The system uses a multi-agent Retrieval-Augmented Generation pipeline to route questions, expand and enrich scientific queries, retrieve evidence from a ChromaDB vector store, rerank candidate chunks with a cross-encoder, generate a grounded draft answer with Gemini, and produce a clean final response with Groq-powered paraphrasing. The result is a chatbot that is optimized for evidence-backed answers with explicit source visibility rather than generic conversational summaries.

## System Architecture
The production pipeline follows seven stages:

1. **Chief Director Agent** decides whether a user message is simple conversation (`chat`) or a technical literature query (`database`). For scientific questions it also assigns one or more tags from `Background`, `Synthesis`, `Characterization`, and `Analysis`.
2. **Query Expander Agent** rewrites the original question into a dense academic retrieval query using PLD/PVD terminology and tag-aware keywords.
3. **HyDE Generator** creates a hypothetical paper-style paragraph so the retrieval query embeds closer to real scientific text chunks.
4. **Dual Retrieval** runs two ChromaDB searches against the `pvd_docs` collection: one using the expanded query embedding and one using the HyDE paragraph embedding. Both paths apply tag-based metadata filters and retrieve candidate chunks.
5. **Hybrid Reranker** merges both retrieval pools, removes duplicates, and reranks the merged set with `cross-encoder/ms-marco-MiniLM-L-6-v2` using the user’s original query as the final relevance signal.
6. **Final Answer Generator** sends the top evidence chunks to Gemini and requests a grounded answer that cites chunk-level support with `[Chunk 1]`, `[Chunk 2]`, and `[Chunk 3]`.
7. **Paraphrase and Citation Restructuring** uses Groq `llama-3.1-8b-instant` to rewrite the answer in cleaner academic language, remove inline chunk markers from the answer body, and append a final citations section derived from the retrieved sources.

## Technology Stack
- Python 3.10+
- FastAPI
- ChromaDB 0.5.5
- `BAAI/bge-small-en-v1.5` for embeddings
- `cross-encoder/ms-marco-MiniLM-L-6-v2` for reranking
- Groq API with `llama-3.1-8b-instant`
- Google Gemini 2.0 Flash with `gemini-flash-latest` fallback
- Next.js
- React
- Vercel for frontend hosting
- Railway or Render for backend hosting
- SQLite for anonymous conversation persistence

## Local Setup — Backend
1. Clone the repository and enter the backend workspace:

   ```bash
   git clone https://github.com/Aads19/UGP_PLD_COPILOT.git
   cd UGP_PLD_COPILOT
   cd backend
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

   On Windows PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. Install the pinned backend dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy the environment template and fill in the required values:

   ```bash
   cp .env.example .env
   ```

   On Windows PowerShell:

   ```powershell
   Copy-Item .env.example .env
   ```

5. Make sure `CHROMA_PATH` points to a valid persisted ChromaDB directory that already contains the `pvd_docs` collection, or rebuild it using the ingestion step below.

6. Start the backend server:

   ```bash
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
   ```

## Local Setup — Frontend
1. Open a new terminal and enter the frontend workspace:

   ```bash
   cd UGP_PLD_COPILOT/frontend
   ```

2. Install Node.js dependencies:

   ```bash
   npm install
   ```

3. Copy the frontend environment template:

   ```bash
   cp .env.local.example .env.local
   ```

   On Windows PowerShell:

   ```powershell
   Copy-Item .env.local.example .env.local
   ```

4. Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local`.

5. Start the frontend:

   ```bash
   npm run dev
   ```

6. Open [http://localhost:3000](http://localhost:3000).

## Building the ChromaDB Database
The vector database only needs to be built once per dataset version. The ingestion pipeline reads `PLD CATEGORY FINAL DATASET.csv`, parses the category tags into boolean metadata fields (`is_Background`, `is_Synthesis`, `is_Characterization`, `is_Analysis`), generates embeddings with `BAAI/bge-small-en-v1.5`, and stores the chunks in a persisted ChromaDB directory.

Use the provided CLI entry point:

```bash
python main.py ingest --config configs/pld_config.example.yaml --reset
```

Before running ingestion:
- Update `configs/pld_config.example.yaml` or provide your own config file.
- Point `chroma.persist_directory` to the directory where the rebuilt ChromaDB should be stored.
- Make sure the CSV path in the config points to the categorized dataset.

After the build completes, set `CHROMA_PATH` in the backend environment to the persisted directory that contains the `pvd_docs` collection.

## Deployment
The recommended deployment split is:

- **Backend** on Railway or Render using the Dockerfile in `backend/`
- **Frontend** on Vercel using the Next.js app in `frontend/`

For backend deployment:
- Set `GROQ_API_KEY`, `GEMINI_API_KEY`, `CHROMA_PATH`, `DATABASE_PATH`, and `FRONTEND_URL`.
- Mount a persistent volume that contains the prebuilt ChromaDB directory.
- Point `CHROMA_PATH` to that mounted directory.
- Expose `/api/health` as the platform health check.

For frontend deployment:
- Set `NEXT_PUBLIC_API_URL` to the full backend base URL, for example `https://your-backend.railway.app`.
- Deploy the `frontend/` folder to Vercel.

## Environment Variables
| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GROQ_API_KEY` | Yes | None | Groq key used by the Director, Query Expander, HyDE, chat reply, and paraphrase stages. |
| `GEMINI_API_KEY` | Yes | None | Gemini key used by the grounded answer generation stage. |
| `CHROMA_PATH` | Yes | `./chroma_db` | Filesystem path to the persisted ChromaDB directory. |
| `DATABASE_PATH` | No | `./conversations.db` | SQLite database file used for anonymous conversation history. |
| `FRONTEND_URL` | Yes for production | None | Frontend origin used in backend CORS configuration. |
| `PORT` | No | `8000` | FastAPI server port in local or hosted environments. |
| `NEXT_PUBLIC_API_URL` | Yes for frontend | None | Base URL of the deployed backend API used by the Next.js frontend. |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Gemini model name for the final answer generator. |
| `LLM_ROUTER_MODEL` | No | `llama-3.1-8b-instant` | Groq model used by the Director. |
| `LLM_REWRITE_MODEL` | No | `llama-3.1-8b-instant` | Groq model used by the Query Expander. |
| `LLM_HYDE_MODEL` | No | `llama-3.1-8b-instant` | Groq model used by the HyDE generator. |
| `LLM_PARAPHRASE_MODEL` | No | `llama-3.1-8b-instant` | Groq model used for final paraphrasing. |
| `EMBEDDING_MODEL_NAME` | No | `BAAI/bge-small-en-v1.5` | SentenceTransformer model used for manual query embeddings and ingestion. |
| `RERANKER_MODEL_NAME` | No | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-encoder model used for reranking retrieval candidates. |
