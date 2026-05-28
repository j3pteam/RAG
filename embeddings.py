"""
Embedding + chunking utilities — Voyage AI version.

Uses Voyage AI's voyage-3-lite model (512 dimensions, free tier: 50M tokens).
Requires VOYAGE_API_KEY environment variable.

Get a key at: https://www.voyageai.com
"""
import os
import re
from typing import Optional

try:
    import voyageai
    HAS_VOYAGE = True
except ImportError:
    HAS_VOYAGE = False

# Maintain the same interface as before — app.py imports `HAS_OPENAI` etc.
# but we'll keep the constant names generic for forward compatibility.
HAS_OPENAI = HAS_VOYAGE  # alias for backward compat with app.py

VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY")
EMBEDDING_MODEL = "voyage-3-lite"  # 512 dims, generous free tier
EMBEDDING_DIM = 512

_client: Optional["voyageai.Client"] = None


def is_enabled() -> bool:
    return HAS_VOYAGE and bool(VOYAGE_API_KEY)


def _get_client():
    global _client
    if _client is None and is_enabled():
        _client = voyageai.Client(api_key=VOYAGE_API_KEY)
    return _client


def embed_text(text: str) -> list:
    """Get embedding vector for a single piece of text (used for queries)."""
    client = _get_client()
    if client is None:
        raise RuntimeError("Voyage API key not configured")
    result = client.embed([text], model=EMBEDDING_MODEL, input_type="query")
    return result.embeddings[0]


def embed_batch(texts: list) -> list:
    """Embed many texts in batches (used for document upload, type=document)."""
    client = _get_client()
    if client is None:
        raise RuntimeError("Voyage API key not configured")
    results = []
    batch_size = 100  # Voyage allows up to 128
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        result = client.embed(batch, model=EMBEDDING_MODEL, input_type="document")
        results.extend(result.embeddings)
    return results


def chunk_text(text: str, target_words: int = 350, overlap_words: int = 50) -> list:
    """Split text into ~350-word chunks with ~50 words of overlap."""
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    current_words = []

    for para in paragraphs:
        para_words = para.split()
        if len(para_words) > target_words * 1.5:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sent in sentences:
                sent_words = sent.split()
                if len(current_words) + len(sent_words) > target_words:
                    if current_words:
                        chunks.append(' '.join(current_words))
                        current_words = current_words[-overlap_words:] if overlap_words else []
                current_words.extend(sent_words)
        else:
            if len(current_words) + len(para_words) > target_words and current_words:
                chunks.append(' '.join(current_words))
                current_words = current_words[-overlap_words:] if overlap_words else []
            current_words.extend(para_words)

    if current_words:
        chunks.append(' '.join(current_words))
    return chunks


def extract_text_from_upload(filename: str, file_bytes: bytes) -> str:
    """Extract text from PDF, DOCX, TXT, or MD."""
    name_lower = filename.lower()

    if name_lower.endswith('.pdf'):
        try:
            from pypdf import PdfReader
            from io import BytesIO
            reader = PdfReader(BytesIO(file_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
            return '\n\n'.join(pages)
        except ImportError:
            raise RuntimeError("pypdf not installed — cannot process PDFs")

    if name_lower.endswith('.docx'):
        try:
            from docx import Document
            from io import BytesIO
            doc = Document(BytesIO(file_bytes))
            return '\n\n'.join(p.text for p in doc.paragraphs if p.text.strip())
        except ImportError:
            raise RuntimeError("python-docx not installed — cannot process .docx")

    if name_lower.endswith(('.txt', '.md', '.markdown')):
        return file_bytes.decode('utf-8', errors='replace')

    raise ValueError(f"Unsupported file type: {filename}. Use PDF, DOCX, TXT, or MD.")
