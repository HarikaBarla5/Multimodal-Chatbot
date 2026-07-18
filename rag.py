"""
Retrieval-Augmented Generation (RAG) support.

Lets the chatbot build a persistent knowledge base from uploaded
documents, then automatically retrieves the most relevant chunks for
every question — instead of relying purely on the model's training data,
or (as file_handler.py does for one-off attachments) dumping an entire
document into a single message.

Pipeline:
    1. Extract plain text from an uploaded file (pdf/txt/docx).
    2. Split that text into overlapping chunks.
    3. Embed each chunk with Gemini's embedding model.
    4. Store chunks + embeddings in a local JSON file.
    5. For every question, embed it the same way and find the stored
       chunks with the highest cosine similarity (plain numpy — no
       external vector database needed for a personal-scale knowledge
       base like this).
    6. Those chunks get folded into the prompt as context before Gemini
       generates its answer.

This deliberately avoids heavier vector-database libraries (e.g.
ChromaDB), which pull in a large dependency chain (grpc, opentelemetry)
that's prone to breaking on Windows. A plain JSON file + numpy cosine
similarity is more than sufficient for a personal knowledge base of a
few hundred to low thousands of chunks, and has zero fragile
dependencies.
"""

import io
import os
import json
import numpy as np
from google import genai
from config import GEMINI_API_KEY

EMBEDDING_MODEL = "gemini-embedding-001"
CHUNK_SIZE = 800        # characters per chunk
CHUNK_OVERLAP = 120     # overlap between consecutive chunks
TOP_K = 4               # how many chunks to retrieve per question
STORE_FILE = "knowledge_base.json"

_client = genai.Client(api_key=GEMINI_API_KEY)


def _load_store():
    if os.path.exists(STORE_FILE):
        with open(STORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_store(store):
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(store, f)


def extract_text(uploaded_file) -> str:
    """Pulls plain text out of an uploaded pdf/txt/docx file."""
    filename = uploaded_file.name.lower()
    file_bytes = uploaded_file.getvalue()

    if filename.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="replace")

    if filename.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if filename.endswith(".docx"):
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)

    raise ValueError(f"Unsupported file type for knowledge base: {filename}")


def chunk_text(text: str, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Splits text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


def embed(text: str):
    result = _client.models.embed_content(model=EMBEDDING_MODEL, contents=text)
    return result.embeddings[0].values


def add_document(uploaded_file):
    """Extracts, chunks, embeds, and stores an uploaded document.
    Returns the number of chunks stored."""
    text = extract_text(uploaded_file)
    chunks = chunk_text(text)

    if not chunks:
        return 0

    store = _load_store()
    for chunk in chunks:
        store.append({
            "text": chunk,
            "source": uploaded_file.name,
            "embedding": embed(chunk),
        })
    _save_store(store)
    return len(chunks)


def has_documents() -> bool:
    return os.path.exists(STORE_FILE) and len(_load_store()) > 0


def query(question: str, top_k=TOP_K):
    """Returns the most relevant stored chunks for a question, as a list
    of (chunk_text, source_filename) tuples. Empty list if nothing stored."""
    store = _load_store()
    if not store:
        return []

    question_vec = np.array(embed(question))
    question_norm = question_vec / (np.linalg.norm(question_vec) + 1e-10)

    scored = []
    for entry in store:
        chunk_vec = np.array(entry["embedding"])
        chunk_norm = chunk_vec / (np.linalg.norm(chunk_vec) + 1e-10)
        similarity = float(np.dot(question_norm, chunk_norm))
        scored.append((similarity, entry["text"], entry["source"]))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]
    return [(text, source) for _, text, source in top]


def list_sources():
    """Returns the distinct filenames currently stored in the knowledge base."""
    store = _load_store()
    return sorted(set(entry["source"] for entry in store))


def clear():
    """Wipes the entire knowledge base."""
    if os.path.exists(STORE_FILE):
        os.remove(STORE_FILE)


def build_augmented_content(user_text: str, retrieved_chunks) -> str:
    """Folds retrieved chunks into the user's message as context. Returns
    plain text ready to send to Gemini. If no chunks were retrieved,
    returns user_text unchanged."""
    if not retrieved_chunks:
        return user_text

    context_block = "\n\n".join(
        f"[From {source}]\n{chunk}" for chunk, source in retrieved_chunks
    )
    return (
        "Use the following context from the user's knowledge base to help "
        "answer, if relevant. If the context doesn't help, just answer "
        "normally.\n\n"
        f"--- CONTEXT ---\n{context_block}\n--- END CONTEXT ---\n\n"
        f"User's question: {user_text}"
    )