"""Postgres + pgvector connection helpers."""

import os

import psycopg
from pgvector.psycopg import register_vector

DSN = os.getenv("DATABASE_URL", "postgresql://rag:rag@localhost:5432/ragdb")


def get_conn(*, register=True):
    conn = psycopg.connect(DSN, autocommit=True)
    if register:
        register_vector(conn)
    return conn


def init_db():
    # Create extension first (without registering the vector type)
    with get_conn(register=False) as conn, conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # Now register the vector type and create tables
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
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
        # Add user_id column to existing documents table if it doesn't exist
        cur.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'documents' AND column_name = 'user_id'
                ) THEN
                    ALTER TABLE documents ADD COLUMN user_id TEXT REFERENCES users(id) ON DELETE CASCADE;
                END IF;
            END $$;
            """
        )
