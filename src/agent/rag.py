"""RAG retrieval module using ChromaDB for the province economy knowledge base."""

from __future__ import annotations

import hashlib
from pathlib import Path

import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")

import chromadb
from chromadb.utils import embedding_functions

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"
CHROMA_DIR = Path(__file__).parent / "chroma_db"

COLLECTION_NAME = "province_economy_kb"

EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"

_ef = None


def _get_ef():
    global _ef
    if _ef is None:
        _ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
    return _ef


def _get_client():
    host = os.environ.get("CHROMA_HOST")
    if host:
        port = int(os.environ.get("CHROMA_PORT", "8000"))
        return chromadb.HttpClient(host=host, port=port)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks by character count, breaking at newlines."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:].strip())
            break
        # Try to break at the last newline within the window
        last_nl = text.rfind("\n", start + chunk_size // 2, end)
        if last_nl != -1:
            end = last_nl
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
    return chunks


def _load_documents() -> tuple[list[str], list[dict], list[str]]:
    """Read all .md files from knowledge dir, chunk them, return (ids, metadatas, documents)."""
    ids: list[str] = []
    metadatas: list[dict] = []
    documents: list[str] = []

    if not KNOWLEDGE_DIR.exists():
        return ids, metadatas, documents

    for md_file in sorted(KNOWLEDGE_DIR.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        chunks = _chunk_text(text)
        for i, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(
                f"{md_file.name}:{i}:{chunk[:50]}".encode()
            ).hexdigest()[:12]
            ids.append(chunk_id)
            metadatas.append({"source": md_file.name, "chunk_index": i})
            documents.append(chunk)

    return ids, metadatas, documents


# ---------------------------------------------------------------------------
# Index management
# ---------------------------------------------------------------------------


def build_index(force: bool = False) -> None:
    """Build or rebuild the ChromaDB index from knowledge files."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = _get_client()

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
        embedding_function=_get_ef(),
    )

    ids, metadatas, documents = _load_documents()
    if not documents:
        return

    existing = set(collection.get()["ids"]) if collection.count() > 0 else set()
    current = set(ids)

    if force:
        # Delete all and re-add
        if existing:
            collection.delete(ids=list(existing))
        collection.add(ids=ids, metadatas=metadatas, documents=documents)  # type: ignore[arg-type]
    else:
        # Incremental: add new, remove deleted
        to_add = current - existing
        to_remove = existing - current

        if to_remove:
            collection.delete(ids=list(to_remove))
        if to_add:
            add_ids = [i for i in ids if i in to_add]
            add_docs = [documents[j] for j, i in enumerate(ids) if i in to_add]
            add_meta = [metadatas[j] for j, i in enumerate(ids) if i in to_add]
            collection.add(ids=add_ids, documents=add_docs, metadatas=add_meta)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def search(query: str, top_k: int = 5) -> list[dict]:
    """Search the knowledge base and return top-k results."""
    client = _get_client()
    try:
        collection = client.get_collection(
            name=COLLECTION_NAME, embedding_function=_get_ef()
        )
    except Exception:
        # Collection doesn't exist yet, build it
        build_index()
        collection = client.get_collection(
            name=COLLECTION_NAME, embedding_function=_get_ef()
        )

    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query], n_results=min(top_k, collection.count())
    )

    output: list[dict] = []
    if results and results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            entry: dict = {"text": doc}
            if results["metadatas"] and results["metadatas"][0]:
                entry["source"] = results["metadatas"][0][i].get("source", "unknown")
            if results["distances"] and results["distances"][0]:
                entry["distance"] = results["distances"][0][i]
            output.append(entry)

    return output


def get_context(query: str, top_k: int = 5) -> str:
    """Search and return concatenated context text."""
    results = search(query, top_k)
    if not results:
        return ""
    parts: list[str] = []
    for r in results:
        source = r.get("source", "未知来源")
        parts.append(f"[{source}]\n{r['text']}")
    return "\n\n---\n\n".join(parts)
