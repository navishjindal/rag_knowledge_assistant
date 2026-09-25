"""FastAPI entrypoint: upload docs, list docs, ask questions."""

import os
import tempfile
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

from . import db, generate, ingest, retrieve  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="RAG Knowledge Assistant", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    rerank: bool = True


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/documents")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported for now")
    doc_id = str(uuid.uuid4())
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        path = tmp.name
    try:
        n_chunks = ingest.ingest_pdf(path, doc_id, file.filename)
    except ValueError as e:
        raise HTTPException(422, str(e))
    finally:
        os.unlink(path)
    return {"doc_id": doc_id, "name": file.filename, "chunks": n_chunks}


@app.get("/documents")
def list_documents():
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT d.id, d.name, d.created_at, COUNT(c.id)
               FROM documents d LEFT JOIN chunks c ON c.doc_id = d.id
               GROUP BY d.id ORDER BY d.created_at DESC"""
        )
        rows = cur.fetchall()
    return [
        {"doc_id": r[0], "name": r[1], "created_at": r[2].isoformat(), "chunks": r[3]}
        for r in rows
    ]


@app.post("/query")
def query(req: QueryRequest):
    sources = retrieve.search(req.question, top_k=req.top_k, rerank=req.rerank)
    if not sources:
        raise HTTPException(404, "No documents ingested yet — upload a PDF first")
    answer = generate.generate_answer(req.question, sources)
    return {
        "answer": answer,
        "citations": [
            {
                "n": i + 1,
                "doc_name": s["doc_name"],
                "page": s["page"],
                "chunk_index": s["chunk_index"],
                "text": s["text"],
                "score": s["score"],
            }
            for i, s in enumerate(sources)
        ],
    }
