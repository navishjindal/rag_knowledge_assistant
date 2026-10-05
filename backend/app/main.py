"""FastAPI entrypoint: auth, upload docs, list docs, ask questions, compare docs."""

import os
import tempfile
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()

from . import db, generate, ingest, retrieve  # noqa: E402
from .auth import (  # noqa: E402
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    get_current_user,
    register,
    login,
)
from .judge import judge_answer  # noqa: E402


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

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")



# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    rerank: bool = True


class CompareRequest(BaseModel):
    question: str = Field(min_length=1)
    doc_ids: list[str] = Field(min_length=2, max_length=2)
    top_k_per_doc: int = Field(default=3, ge=1, le=10)
    rerank: bool = True


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
@app.post("/auth/register", response_model=TokenResponse)
def auth_register(req: RegisterRequest):
    return register(req)


@app.post("/auth/login", response_model=TokenResponse)
def auth_login(req: LoginRequest):
    return login(req)


@app.get("/auth/me")
def auth_me(user_id: str = Depends(get_current_user)):
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, email, name, created_at FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "User not found")
    return {"user_id": row[0], "email": row[1], "name": row[2], "created_at": row[3].isoformat()}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Document management (auth-gated)
# ---------------------------------------------------------------------------
@app.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported for now")
    doc_id = str(uuid.uuid4())
    path = os.path.join(UPLOAD_DIR, f"{doc_id}.pdf")
    with open(path, "wb") as f:
        f.write(await file.read())
    try:
        n_chunks = ingest.ingest_pdf(path, doc_id, file.filename, user_id=user_id)
    except ValueError as e:
        os.unlink(path)
        raise HTTPException(422, str(e))
    return {"doc_id": doc_id, "name": file.filename, "chunks": n_chunks}


@app.get("/documents")
def list_documents(user_id: str = Depends(get_current_user)):
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT d.id, d.name, d.created_at, COUNT(c.id)
               FROM documents d LEFT JOIN chunks c ON c.doc_id = d.id
               WHERE d.user_id = %s
               GROUP BY d.id ORDER BY d.created_at DESC""",
            (user_id,),
        )
        rows = cur.fetchall()
    return [
        {"doc_id": r[0], "name": r[1], "created_at": r[2].isoformat(), "chunks": r[3]}
        for r in rows
    ]


@app.delete("/documents/{doc_id}")
def delete_document(doc_id: str, user_id: str = Depends(get_current_user)):
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM documents WHERE id = %s AND user_id = %s RETURNING id",
            (doc_id, user_id),
        )
        deleted = cur.fetchone()
    if not deleted:
        raise HTTPException(404, "Document not found or not owned by you")
    return {"deleted": doc_id}


# ---------------------------------------------------------------------------
# Query (auth-gated, per-user scoped)
# ---------------------------------------------------------------------------
@app.post("/query")
def query(req: QueryRequest, user_id: str = Depends(get_current_user)):
    sources = retrieve.search(
        req.question, top_k=req.top_k, rerank=req.rerank, user_id=user_id
    )
    if not sources:
        raise HTTPException(404, "No documents ingested yet — upload a PDF first")
    answer = generate.generate_answer(req.question, sources)

    # LLM-as-judge faithfulness scoring
    judgment = judge_answer(req.question, answer, sources)

    return {
        "answer": answer,
        "faithfulness": judgment,
        "citations": [
            {
                "n": i + 1,
                "doc_id": s.get("doc_id", ""),
                "doc_name": s["doc_name"],
                "page": s["page"],
                "chunk_index": s["chunk_index"],
                "text": s["text"],
                "score": s["score"],
            }
            for i, s in enumerate(sources)
        ],
    }


# ---------------------------------------------------------------------------
# Multi-document comparison (auth-gated)
# ---------------------------------------------------------------------------
@app.post("/compare")
def compare(req: CompareRequest, user_id: str = Depends(get_current_user)):
    """Compare content across two documents."""
    # Verify both docs belong to this user
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, name FROM documents WHERE id = ANY(%s) AND user_id = %s",
            (req.doc_ids, user_id),
        )
        doc_rows = cur.fetchall()

    if len(doc_rows) != 2:
        raise HTTPException(404, "One or both documents not found (or not owned by you)")

    doc_map = {r[0]: r[1] for r in doc_rows}
    doc_a_id, doc_b_id = req.doc_ids
    doc_a_name = doc_map[doc_a_id]
    doc_b_name = doc_map[doc_b_id]

    # Retrieve from each doc separately
    per_doc = retrieve.search_per_document(
        req.question,
        doc_ids=req.doc_ids,
        top_k_per_doc=req.top_k_per_doc,
        rerank=req.rerank,
        user_id=user_id,
    )

    doc_a_sources = per_doc.get(doc_a_id, [])
    doc_b_sources = per_doc.get(doc_b_id, [])

    if not doc_a_sources and not doc_b_sources:
        raise HTTPException(404, "No relevant content found in either document")

    answer = generate.generate_comparison(
        req.question, doc_a_name, doc_a_sources, doc_b_name, doc_b_sources
    )

    # Judge the comparison answer using combined sources
    all_sources = doc_a_sources + doc_b_sources
    judgment = judge_answer(req.question, answer, all_sources)

    return {
        "answer": answer,
        "faithfulness": judgment,
        "doc_a": {
            "doc_id": doc_a_id,
            "name": doc_a_name,
            "citations": [
                {
                    "n": f"A{i + 1}",
                    "doc_name": doc_a_name,
                    "page": s["page"],
                    "chunk_index": s["chunk_index"],
                    "text": s["text"],
                    "score": s["score"],
                }
                for i, s in enumerate(doc_a_sources)
            ],
        },
        "doc_b": {
            "doc_id": doc_b_id,
            "name": doc_b_name,
            "citations": [
                {
                    "n": f"B{i + 1}",
                    "doc_name": doc_b_name,
                    "page": s["page"],
                    "chunk_index": s["chunk_index"],
                    "text": s["text"],
                    "score": s["score"],
                }
                for i, s in enumerate(doc_b_sources)
            ],
        },
    }
