"""
Embedding + chunking utilities.

Uses OpenAI's text-embedding-3-small model (1536 dimensions, ~$0.02/1M tokens).
Requires OPENAI_API_KEY environment variable.

Falls back gracefully when no key is set.
"""
import os
import re
from typing import Optional

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"

# Lazy client init so missing key doesn't crash app startup
_client: Optional["OpenAI"] = None


def is_enabled() -> bool:
    return HAS_OPENAI and bool(OPENAI_API_KEY)


def _get_client():
    global _client
    if _client is None and is_enabled():
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def embed_text(text: str) -> list:
    """Get embedding vector for a single piece of text."""
    client = _get_client()
    if client is None:
        raise RuntimeError("OpenAI API key not configured")
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


def embed_batch(texts: list) -> list:
    """Embed many texts in one API call (cheaper, faster). Max ~2048 inputs per call."""
    client = _get_client()
    if client is None:
        raise RuntimeError("OpenAI API key not configured")
    # OpenAI accepts up to 2048 inputs per request; chunk if needed
    results = []
    batch_size = 100  # conservative for stability
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        results.extend([item.embedding for item in response.data])
    return results


def chunk_text(text: str, target_words: int = 350, overlap_words: int = 50) -> list:
    """
    Split text into ~350-word chunks with ~50 words of overlap.
    Tries to break on paragraph boundaries when possible, falls back to sentences.
    """
    # Normalize whitespace
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    if not text:
        return []

    # Split by paragraphs first
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

    chunks = []
    current_words = []

    for para in paragraphs:
        para_words = para.split()

        # If this paragraph alone exceeds target, split it further on sentences
        if len(para_words) > target_words * 1.5:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sent in sentences:
                sent_words = sent.split()
                if len(current_words) + len(sent_words) > target_words:
                    if current_words:
                        chunks.append(' '.join(current_words))
                        # Carry overlap from end of previous chunk
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
    """Extract text from a file based on extension. Returns plain text."""
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
