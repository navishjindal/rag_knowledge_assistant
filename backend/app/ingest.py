"""PDF ingestion: parse -> chunk -> embed -> store."""

from pypdf import PdfReader

from . import db
from .embeddings import embed_texts


def chunk_text(text: str, size: int = 2000, overlap: int = 200) -> list[str]:
    """Char-based chunks that prefer to break at paragraph/sentence boundaries."""
    chunks, start, n = [], 0, len(text)
    while start < n:
        end = min(start + size, n)
        if end < n:
            cut = text.rfind("\n\n", start, end)
            if cut == -1:
                cut = text.rfind(". ", start, end)
            if cut != -1 and cut > start + size // 2:
                end = cut + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        start = end - overlap if end < n else n
    return chunks


def ingest_pdf(path: str, doc_id: str, name: str, user_id: str | None = None) -> int:
    """Ingest a PDF: parse pages, chunk text, embed, and store.

    Args:
        path: Local path to the PDF file.
        doc_id: Unique document identifier.
        name: Original filename.
        user_id: Owner user ID (None for legacy/anonymous usage).
    """
    reader = PdfReader(path)
    rows: list[tuple[int, int, str]] = []
    for page_no, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        for i, chunk in enumerate(chunk_text(text)):
            rows.append((page_no, i, chunk))
    if not rows:
        raise ValueError("No extractable text found in PDF")

    embeddings = embed_texts([r[2] for r in rows])

    with db.get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (id, name, user_id) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (doc_id, name, user_id),
        )
        for (page_no, chunk_index, text), emb in zip(rows, embeddings):
            cur.execute(
                """INSERT INTO chunks (doc_id, page, chunk_index, text, embedding)
                   VALUES (%s, %s, %s, %s, %s)""",
                (doc_id, page_no, chunk_index, text, emb),
            )
    return len(rows)
