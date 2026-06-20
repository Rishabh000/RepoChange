"""ChromaDB-backed semantic memory.

Stores a record per file: {filename, summary, content} and supports semantic
search over them. Embeddings are produced locally with sentence-transformers,
so search works without any API key.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import CHROMA_DIR, ensure_dirs  # noqa: E402

_COLLECTION = "repo_memory"
_EMBED_MODEL = "all-MiniLM-L6-v2"

# Module-level singletons so the (heavy) model loads only once per process.
_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection

    import chromadb
    from chromadb.utils import embedding_functions

    ensure_dirs()
    _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=_EMBED_MODEL
    )
    _collection = _client.get_or_create_collection(
        name=_COLLECTION,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )
    return _collection


def remember(filename: str, summary: str, content: str = "") -> dict:
    """Upsert a file's summary + content into the vector store.

    The document that gets embedded is the summary plus a content excerpt, which
    gives good recall for natural-language queries.
    """
    collection = _get_collection()
    document = summary if not content else f"{summary}\n\n{content[:2000]}"
    collection.upsert(
        ids=[filename],
        documents=[document],
        metadatas=[{"filename": filename, "summary": summary}],
    )
    return {"remembered": filename, "summary": summary}


def search_memory(query: str, n_results: int = 5) -> list[dict]:
    """Return the closest stored files for a natural-language query."""
    collection = _get_collection()
    count = collection.count()
    if count == 0:
        return []
    res = collection.query(query_texts=[query], n_results=min(n_results, count))
    hits = []
    ids = res.get("ids", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    for i, _id in enumerate(ids):
        meta = metas[i] or {}
        distance = dists[i] if i < len(dists) else None
        hits.append({
            "filename": meta.get("filename", _id),
            "summary": meta.get("summary", ""),
            "score": round(1 - distance, 4) if distance is not None else None,
        })
    return hits


def reset_memory() -> dict:
    """Drop all stored memories (useful for repeatable demos)."""
    import chromadb

    ensure_dirs()
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(_COLLECTION)
    except Exception:
        pass
    global _client, _collection
    _client = None
    _collection = None
    return {"reset": True}
