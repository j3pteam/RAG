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
            # Add learning columns (approved-as-lesson + question embedding)
            cur.execute(f"""
                ALTER TABLE feedback ADD COLUMN IF NOT EXISTS approved_for_learning BOOLEAN DEFAULT FALSE;
            """)
            cur.execute(f"""
                ALTER TABLE feedback ADD COLUMN IF NOT EXISTS question_embedding vector({EMBEDDING_DIM});
            """)
            # Index for fast similarity search on approved lessons
            cur.execute("""
                CREATE INDEX IF NOT EXISTS feedback_lesson_idx
                ON feedback USING hnsw (question_embedding vector_cosine_ops)
                WHERE approved_for_learning = TRUE AND question_embedding IS NOT NULL;
            """)
        conn.commit()
    return True


def _table_exists(cur, table_name: str) -> bool:
    cur.execute(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s);",
        (table_name,),
    )
    return cur.fetchone()["exists"]


def find_duplicate_document(title: str = "", source: str = "") -> Optional[dict]:
    """
    Check whether a document with the same title OR source already exists.

    Matching is case-insensitive on both fields. Either match counts as a duplicate
    because users sometimes re-upload the same file with a different title or
    re-ingest the same URL with a different display name.

    Returns the existing document row (with id, title, source, uploaded_at, chunk_count)
    or None if no duplicate found.
    """
    if not is_enabled():
        return None
    title_norm = (title or "").strip().lower()
    source_norm = (source or "").strip().lower()
    if not title_norm and not source_norm:
        return None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, source, uploaded_at, chunk_count
                FROM documents
                WHERE (%s <> '' AND LOWER(TRIM(title)) = %s)
                   OR (%s <> '' AND LOWER(TRIM(source)) = %s)
                ORDER BY uploaded_at DESC
                LIMIT 1;
                """,
                (title_norm, title_norm, source_norm, source_norm),
            )
            return cur.fetchone()


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
                (rating, user_message[:8000], bot_reply[:20000], comment[:4000], persona[:100]),
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


def delete_feedback_ids(ids: list) -> int:
    """Delete specific feedback rows by ID. Returns count deleted."""
    if not is_enabled() or not ids:
        return 0
    clean_ids = [int(i) for i in ids if str(i).isdigit()]
    if not clean_ids:
        return 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM feedback WHERE id = ANY(%s);", (clean_ids,))
            count = cur.rowcount
        conn.commit()
        return count


def delete_all_feedback() -> int:
    """Wipe all feedback rows. Returns count deleted."""
    if not is_enabled():
        return 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM feedback;")
            count = cur.rowcount
        conn.commit()
        return count


def approve_feedback_as_lesson(feedback_id: int, question_embedding: list) -> bool:
    """Mark a thumbs-down feedback row as approved for use as a learning example.

    The question embedding is stored at approval time (not at feedback time) so
    that we only spend embedding tokens on items that actually get used.
    Returns True if approved, False if row not found or not eligible.
    """
    if not is_enabled():
        return False
    embedding_str = "[" + ",".join(str(x) for x in question_embedding) + "]"
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Only approve rows that are thumbs-down AND have a comment
            cur.execute(
                """
                UPDATE feedback
                SET approved_for_learning = TRUE,
                    question_embedding = %s::vector
                WHERE id = %s
                  AND rating = 'down'
                  AND comment IS NOT NULL
                  AND TRIM(comment) <> '';
                """,
                (embedding_str, feedback_id),
            )
            updated = cur.rowcount
        conn.commit()
        return updated > 0


def revoke_feedback_lesson(feedback_id: int) -> bool:
    """Remove approval — this lesson stops influencing future responses."""
    if not is_enabled():
        return False
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE feedback SET approved_for_learning = FALSE WHERE id = %s;",
                (feedback_id,),
            )
            updated = cur.rowcount
        conn.commit()
        return updated > 0


def get_feedback(feedback_id: int) -> Optional[dict]:
    """Fetch a single feedback row by ID."""
    if not is_enabled():
        return None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM feedback WHERE id = %s;", (feedback_id,))
            return cur.fetchone()


def search_lessons(query_embedding: list, limit: int = 3, min_similarity: float = 0.5) -> list:
    """Find approved lessons whose user-question is semantically similar to the
    current question. Used at chat time to inject 'what to avoid' guidance.

    Returns rows with: user_message, bot_reply, comment, similarity.
    Only returns rows above min_similarity to avoid distracting the bot with
    weakly related lessons.
    """
    if not is_enabled():
        return []
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id, user_message, bot_reply, comment,
                    1 - (question_embedding <=> %s::vector) AS similarity
                FROM feedback
                WHERE approved_for_learning = TRUE
                  AND question_embedding IS NOT NULL
                ORDER BY question_embedding <=> %s::vector
                LIMIT %s;
                """,
                (embedding_str, embedding_str, limit),
            )
            rows = list(cur.fetchall())
            return [r for r in rows if r.get("similarity", 0) >= min_similarity]


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
