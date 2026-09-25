# RAG Knowledge Assistant

Ask questions over your own documents. Upload PDFs, get answers **with citations**
back to the exact source passages.

Built to demonstrate retrieval-augmented generation end to end:
document ingestion → chunking → embeddings → vector search → reranking →
grounded generation → evaluation.

## Architecture

```
┌──────────┐   upload PDF    ┌──────────────┐   chunks + embeddings   ┌─────────────┐
│  React   │ ─────────────▶ │   FastAPI    │ ──────────────────────▶ │  Postgres   │
│ frontend │                │   backend    │                         │  + pgvector │
└──────────┘ ◀───────────── └──────────────┘ ◀────────────────────── └─────────────┘
   │ chat UI +            │  /documents      answer + citations
   │ citation viewer      │  /query
                          │
                          ▼
                   ┌──────────────┐
                   │ LLM (Gemini  │
                   │  or Groq)    │
                   └──────────────┘
```

Pipeline per query:

1. Embed the question (`all-MiniLM-L6-v2`, local, free).
2. Cosine-similarity search over chunk embeddings in pgvector → top candidates.
3. Rerank with a cross-encoder (`ms-marco-MiniLM-L-6-v2`) → keep top-k.
4. Build a prompt with numbered sources; LLM answers **only from context**,
   citing `[1]`, `[2]`, … and refusing when the context doesn't cover it.

## Quickstart

```bash
# 1. Configure
cp .env.example .env
# add your GEMINI_API_KEY (or GROQ_API_KEY + LLM_PROVIDER=groq)

# 2. Start Postgres + API
docker compose up --build

# 3. Ingest a PDF (API docs at http://localhost:8000/docs)
curl -X POST http://localhost:8000/documents -F "file=@notes.pdf"

# 4. Ask
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What does the document say about chunking?"}'

# 5. Frontend
cd frontend && npm install && npm run dev   # http://localhost:5173
```

## Evaluation (the part interviewers care about)

`evals/` ships a golden question set and a runner that measures:

- **Retrieval recall@k** — did the right chunk come back?
- **Answer keyword faithfulness** — did the answer contain the expected facts?

```bash
python evals/run_eval.py --api http://localhost:8000 --set evals/golden_set.json
```

Workflow: ingest docs → write 20–30 questions with known answers →
run eval → change something (chunk size, rerank on/off, prompt) →
run eval again → record the delta in the table below. That delta is your
resume bullet.

| Change | Recall@5 | Faithfulness | Notes |
|--------|----------|--------------|-------|
| baseline (top-5, no rerank) | — | — | |
| + cross-encoder rerank | — | — | |

## Roadmap (stretch goals)

- Hybrid search: BM25 + vector with reciprocal rank fusion
- Streaming answers (SSE) so the UI feels instant
- LLM-as-judge faithfulness scoring instead of keyword checks
- Multi-document comparison questions ("how do doc A and doc B differ?")
- Auth + per-user document namespaces

## Resume bullets (fill in your numbers)

- Built a RAG Q&A system over user-uploaded PDFs: FastAPI + pgvector,
  cross-encoder reranking, and cited answers via Gemini/Groq.
- Lifted answer faithfulness from X% → Y% (30-question eval set) by adding
  reranking and tuning chunk size.
- Deployed with Docker Compose; React frontend with click-to-source
  citation viewer.
