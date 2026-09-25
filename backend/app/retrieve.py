"""Retrieval: vector search + optional cross-encoder rerank."""

from . import db
from .embeddings import embed_query


def search(question: str, top_k: int = 5, rerank: bool = True) -> list[dict]:
    qvec = embed_query(question)
    fetch = top_k * 2 if rerank else top_k
    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.id, d.name, c.page, c.chunk_index, c.text,
                   1 - (c.embedding <=> %s::vector) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.doc_id
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
            """,
            (qvec, qvec, fetch),
        )
        rows = cur.fetchall()

    results = [
        {
            "chunk_id": r[0],
            "doc_name": r[1],
            "page": r[2],
            "chunk_index": r[3],
            "text": r[4],
            "score": float(r[5]),
        }
        for r in rows
    ]
    if rerank and len(results) > top_k:
        results = rerank_results(question, results, top_k)
    return results[:top_k]


def rerank_results(question: str, results: list[dict], top_k: int) -> list[dict]:
    from sentence_transformers import CrossEncoder

    ce = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    scores = ce.predict([(question, r["text"]) for r in results])
    ranked = sorted(zip(scores, results), key=lambda pair: -pair[0])
    return [{**r, "rerank_score": float(s)} for s, r in ranked][:top_k]
