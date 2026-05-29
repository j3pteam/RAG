"""
Database layer for the J3P knowledge base.

Uses Railway Postgres with the pgvector extension for semantic search.
Tables:
  documents  - one row per uploaded document (title, source, upload time)
  chunks     - chunks of text from documents, each with a vector embedding
  feedback   - thumbs up/down ratings with full context

Falls back gracefully when DATABASE_URL is not set (RAG simply disabled).
"""
import os
from contextlib import contextmanager
from typing import Optional

try:
    import psycopg
    from psycopg.rows import dict_row
    HAS_PSYCOPG = True
except ImportError:
    HAS_PSYCOPG = False


DATABASE_URL = os.environ.get("DATABASE_URL")
EMBEDDING_DIM = 512  # voyage-3-lite


def is_enabled() -> bool:
    """RAG is available only when both psycopg is installed and DB URL is set."""
    return HAS_PSYCOPG and bool(DATABASE_URL)


@contextmanager
def get_conn():
    """Yield a Postgres connection. Caller is responsible for transactions."""
    if not is_enabled():
        raise RuntimeError("Database not configured")
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def init_schema():
    """Create tables and pgvector extension if they don't exist. Idempotent.
    If an existing chunks table has the wrong embedding dimension, drops & recreates it.
    """
    if not is_enabled():
        return False
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    source TEXT,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    chunk_count INT DEFAULT 0
                );
            """)
            # Check if chunks table exists with mismatched embedding dimension
            cur.execute("""
                SELECT atttypmod FROM pg_attribute
                WHERE attrelid = 'chunks'::regclass AND attname = 'embedding';
            """) if _table_exists(cur, 'chunks') else None

            needs_recreate = False
            if _table_exists(cur, 'chunks'):
                cur.execute("""
                    SELECT a.atttypmod FROM pg_attribute a
                    JOIN pg_class c ON a.attrelid = c.oid
                    WHERE c.relname = 'chunks' AND a.attname = 'embedding';
                """)
                row = cur.fetchone()
                if row and row.get("atttypmod") and row["atttypmod"] != EMBEDDING_DIM:
                    needs_recreate = True

            if needs_recreate:
                cur.execute("DROP TABLE IF EXISTS chunks CASCADE;")
                cur.execute("DELETE FROM documents;")  # clear stale doc rows since chunks are gone

            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS chunks (
                    id SERIAL PRIMARY KEY,
                    document_id INT REFERENCES documents(id) ON DELETE CASCADE,
                    chunk_index INT NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector({EMBEDDING_DIM})
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS chunks_embedding_idx
                ON chunks USING hnsw (embedding vector_cosine_ops);
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    rating TEXT CHECK (rating IN ('up', 'down')),
                    user_message TEXT,
                    bot_reply TEXT,
                    comment TEXT,
                    persona TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Add comment column to existing tables that pre-date it
            cur.execute("""
                ALTER TABLE feedback ADD COLUMN IF NOT EXISTS comment TEXT;
            """)
        conn.commit()
    return True


def _table_exists(cur, table_name: str) -> bool:
    cur.execute(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s);",
        (table_name,),
    )
    return cur.fetchone()["exists"]


def insert_document(title: str, source: str, chunks_with_embeddings: list) -> int:
    """
    Insert a document and its chunks in one transaction.
    chunks_with_embeddings: list of (text, embedding_list) tuples.
    Returns the new document id.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents (title, source, chunk_count) VALUES (%s, %s, %s) RETURNING id;",
                (title, source, len(chunks_with_embeddings)),
            )
            doc_id = cur.fetchone()["id"]
            for idx, (text, embedding) in enumerate(chunks_with_embeddings):
                # Format embedding as pgvector literal: '[0.1,0.2,...]'
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
                cur.execute(
                    "INSERT INTO chunks (document_id, chunk_index, content, embedding) "
                    "VALUES (%s, %s, %s, %s);",
                    (doc_id, idx, text, embedding_str),
                )
        conn.commit()
    return doc_id


def search_chunks(query_embedding: list, limit: int = 5) -> list:
    """Return the top-N most semantically similar chunks for a query embedding."""
    if not is_enabled():
        return []
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.content, c.chunk_index, d.title, d.id AS doc_id,
                       1 - (c.embedding <=> %s::vector) AS similarity
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s;
                """,
                (embedding_str, embedding_str, limit),
            )
            return list(cur.fetchall())


def list_documents() -> list:
    """Return all uploaded documents, newest first."""
    if not is_enabled():
        return []
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, source, uploaded_at, chunk_count "
                "FROM documents ORDER BY uploaded_at DESC;"
            )
            return list(cur.fetchall())


def delete_document(doc_id: int):
    """Delete a document and all its chunks (cascade)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id = %s;", (doc_id,))
        conn.commit()


def log_feedback(rating: str, user_message: str, bot_reply: str, persona: str = "", comment: str = ""):
    """Persist a thumbs up/down rating with optional comment."""
    if not is_enabled():
        return  # silently no-op; logging-only mode
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO feedback (rating, user_message, bot_reply, comment, persona) "
                "VALUES (%s, %s, %s, %s, %s);",
                (rating, user_message[:2000], bot_reply[:2000], comment[:2000], persona[:100]),
            )
        conn.commit()


def list_feedback(limit: int = 100, rating: Optional[str] = None) -> list:
    """Return recent feedback for the admin view."""
    if not is_enabled():
        return []
    with get_conn() as conn:
        with conn.cursor() as cur:
            if rating in ("up", "down"):
                cur.execute(
                    "SELECT * FROM feedback WHERE rating = %s "
                    "ORDER BY created_at DESC LIMIT %s;",
                    (rating, limit),
                )
            else:
                cur.execute(
                    "SELECT * FROM feedback ORDER BY created_at DESC LIMIT %s;",
                    (limit,),
                )
            return list(cur.fetchall())


def feedback_stats() -> dict:
    """Aggregate counts for the admin dashboard."""
    if not is_enabled():
        return {"up": 0, "down": 0, "total": 0}
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT rating, COUNT(*) as n FROM feedback GROUP BY rating;"
            )
            counts = {row["rating"]: row["n"] for row in cur.fetchall()}
    up = counts.get("up", 0)
    down = counts.get("down", 0)
    return {"up": up, "down": down, "total": up + down}
