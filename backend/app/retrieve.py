"""Retrieval: vector search + optional cross-encoder rerank.

Supports per-user document filtering and multi-document scoped retrieval.
"""

from . import db
from .embeddings import embed_query


def search(
    question: str,
    top_k: int = 5,
    rerank: bool = True,
    user_id: str | None = None,
    doc_ids: list[str] | None = None,
) -> list[dict]:
    """Search chunks by cosine similarity, optionally filtering by user and/or doc IDs.

    Args:
        question: The user's question.
        top_k: Number of results to return.
        rerank: Whether to apply cross-encoder reranking.
        user_id: If set, only search this user's documents.
        doc_ids: If set, only search these specific documents.
    """
    qvec = embed_query(question)
    fetch = top_k * 2 if rerank else top_k

    # Build dynamic WHERE clause
    conditions = []
    where_params = []

    if user_id:
        conditions.append("d.user_id = %s")
        where_params.append(user_id)
    if doc_ids:
        conditions.append("d.id = ANY(%s)")
        where_params.append(doc_ids)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    # The order of %s in the query is: SELECT (qvec), WHERE (where_params), ORDER BY (qvec), LIMIT (fetch)
    params = [qvec] + where_params + [qvec, fetch]

    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT c.id, d.id, d.name, c.page, c.chunk_index, c.text,
                   1 - (c.embedding <=> %s::vector) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.doc_id
            {where}
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
            """,
            params,
        )
        rows = cur.fetchall()

    results = [
        {
            "chunk_id": r[0],
            "doc_id": r[1],
            "doc_name": r[2],
            "page": r[3],
            "chunk_index": r[4],
            "text": r[5],
            "score": float(r[6]),
        }
        for r in rows
    ]
    if rerank and len(results) > top_k:
        results = rerank_results(question, results, top_k)
    return results[:top_k]


def search_per_document(
    question: str,
    doc_ids: list[str],
    top_k_per_doc: int = 3,
    rerank: bool = True,
    user_id: str | None = None,
) -> dict[str, list[dict]]:
    """Retrieve top-k chunks from each document separately for comparison queries.

    Returns a dict mapping doc_id -> list of chunk dicts.
    """
    results = {}
    for doc_id in doc_ids:
        results[doc_id] = search(
            question,
            top_k=top_k_per_doc,
            rerank=rerank,
            user_id=user_id,
            doc_ids=[doc_id],
        )
    return results


def rerank_results(question: str, results: list[dict], top_k: int) -> list[dict]:
    from sentence_transformers import CrossEncoder

    ce = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    scores = ce.predict([(question, r["text"]) for r in results])
    ranked = sorted(zip(scores, results), key=lambda pair: -pair[0])
    return [{**r, "rerank_score": float(s)} for s, r in ranked][:top_k]
