"""Postgres + pgvector connection helpers."""

import os

import psycopg
from pgvector.psycopg import register_vector

DSN = os.getenv("DATABASE_URL", "postgresql://rag:rag@localhost:5432/ragdb")


def get_conn():
    conn = psycopg.connect(DSN, autocommit=True)
    register_vector(conn)
    return conn


def init_db():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id SERIAL PRIMARY KEY,
                doc_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
                page INT NOT NULL,
                chunk_index INT NOT NULL,
                text TEXT NOT NULL,
                embedding vector(384) NOT NULL
            )
            """
        )
