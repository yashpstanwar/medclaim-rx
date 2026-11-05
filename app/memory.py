"""ChromaDB Clinical Policy RAG Memory for MedClaim Rx.

Embeds and queries clinical policies from data/clinical_policy.md using
sentence-transformers/all-MiniLM-L6-v2 and persistent Chroma storage.
Enforces fail-closed behavior on empty or missing collections.
"""

import os
from pathlib import Path
from typing import List, Optional
import math
import re

# Model constant as specified
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_COLLECTION_NAME = "clinical_policies"
DEFAULT_CHROMA_DIR = ".chroma"
DEFAULT_POLICY_PATH = "data/clinical_policy.md"

try:
    import chromadb
    from chromadb.utils import embedding_functions

    CHROMA_AVAILABLE = True
except ImportError:
    chromadb = None
    embedding_functions = None
    CHROMA_AVAILABLE = False


class _FallbackPolicyStore:
    """Lightweight in-memory/file fallback when chromadb package is not yet installed."""

    def __init__(self, persist_dir: str = DEFAULT_CHROMA_DIR):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._collections: dict[str, list[dict]] = {}

    def get_or_create_collection(self, name: str):
        if name not in self._collections:
            self._collections[name] = []
        return self

    def delete_collection(self, name: str):
        self._collections.pop(name, None)

    def count(self, collection_name: str = DEFAULT_COLLECTION_NAME) -> int:
        return len(self._collections.get(collection_name, []))

    def upsert(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[dict]] = None,
    ):
        if collection_name not in self._collections:
            self._collections[collection_name] = []

        existing = {item["id"]: item for item in self._collections[collection_name]}
        for idx, doc_id in enumerate(ids):
            meta = metadatas[idx] if metadatas and idx < len(metadatas) else {}
            existing[doc_id] = {"id": doc_id, "document": documents[idx], "metadata": meta}
        self._collections[collection_name] = list(existing.values())

    def query(
        self, collection_name: str, query_text: str, n_results: int = 3
    ) -> List[str]:
        items = self._collections.get(collection_name, [])
        if not items:
            return []

        def _tokenize(text: str) -> set[str]:
            return set(re.findall(r"\w+", text.lower()))

        query_tokens = _tokenize(query_text)
        if not query_tokens:
            return [it["document"] for it in items[:n_results]]

        scored = []
        for it in items:
            doc_tokens = _tokenize(it["document"])
            overlap = len(query_tokens & doc_tokens)
            score = overlap / math.sqrt(len(query_tokens) * (len(doc_tokens) + 1e-5))
            scored.append((score, it["document"]))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored[:n_results] if score > 0] or [
            it["document"] for it in items[:n_results]
        ]


_fallback_instance: Optional[_FallbackPolicyStore] = None


def _get_fallback_store(persist_dir: str) -> _FallbackPolicyStore:
    global _fallback_instance
    if _fallback_instance is None or str(_fallback_instance.persist_dir) != persist_dir:
        _fallback_instance = _FallbackPolicyStore(persist_dir)
    return _fallback_instance


def get_embedding_function():
    """Retrieve sentence-transformers embedding function if available."""
    if CHROMA_AVAILABLE and embedding_functions is not None:
        try:
            return embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
        except Exception:
            return None
    return None


def get_chroma_client(persist_dir: str = DEFAULT_CHROMA_DIR):
    """Obtain persistent Chroma client or fallback store."""
    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    if CHROMA_AVAILABLE and chromadb is not None:
        return chromadb.PersistentClient(path=persist_dir)
    return _get_fallback_store(persist_dir)


def seed_policy(
    policy_path: str = DEFAULT_POLICY_PATH,
    persist_dir: str = DEFAULT_CHROMA_DIR,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> int:
    """Parse policy markdown file and seed non-heading rule chunks into Chroma.

    Args:
        policy_path: Path to clinical_policy.md.
        persist_dir: Chroma persistent directory.
        collection_name: Target Chroma collection name.

    Returns:
        Number of policy chunks indexed.
    """
    path = Path(policy_path)
    if not path.exists():
        raise FileNotFoundError(f"Policy file not found: {policy_path}")

    # Extract non-heading, non-blank lines
    chunks: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            chunks.append(stripped)

    if not chunks:
        return 0

    client = get_chroma_client(persist_dir)
    ids = [f"rule_{i+1:03d}" for i in range(len(chunks))]
    metadatas = [{"source": path.name, "rule_index": i + 1} for i in range(len(chunks))]

    if CHROMA_AVAILABLE and hasattr(client, "get_or_create_collection"):
        emb_fn = get_embedding_function()
        if emb_fn:
            collection = client.get_or_create_collection(
                name=collection_name, embedding_function=emb_fn
            )
        else:
            collection = client.get_or_create_collection(name=collection_name)

        collection.upsert(
            ids=ids,
            documents=chunks,
            metadatas=metadatas,
        )
    else:
        # Fallback store
        client.upsert(
            collection_name=collection_name,
            ids=ids,
            documents=chunks,
            metadatas=metadatas,
        )

    return len(chunks)


def retrieve_policy_chunks(
    query: str,
    n_results: int = 3,
    persist_dir: str = DEFAULT_CHROMA_DIR,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> List[str]:
    """Retrieve top relevant clinical policy chunks from Chroma vector index.

    Enforces fail-closed behavior: returns [] if collection is empty or missing.

    Args:
        query: Clinical search query (e.g. 'biologic cost limit').
        n_results: Maximum number of chunks to return.
        persist_dir: Chroma persistent directory.
        collection_name: Target Chroma collection name.

    Returns:
        List of matching policy rule strings, or [] if empty/fail-closed.
    """
    client = get_chroma_client(persist_dir)

    if CHROMA_AVAILABLE and hasattr(client, "get_or_create_collection"):
        try:
            emb_fn = get_embedding_function()
            if emb_fn:
                collection = client.get_or_create_collection(
                    name=collection_name, embedding_function=emb_fn
                )
            else:
                collection = client.get_or_create_collection(name=collection_name)

            if collection.count() == 0:
                # Fail-closed: empty shelf returns empty list
                return []

            results = collection.query(
                query_texts=[query],
                n_results=min(n_results, collection.count()),
            )
            docs = results.get("documents", [])
            if docs and len(docs) > 0:
                return docs[0]
            return []
        except Exception:
            # On vector error, fail-closed
            return []
    else:
        store = _get_fallback_store(persist_dir)
        if store.count(collection_name) == 0:
            return []
        return store.query(
            collection_name=collection_name, query_text=query, n_results=n_results
        )


def reset_policy_collection(
    persist_dir: str = DEFAULT_CHROMA_DIR,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> bool:
    """Clear collection for test isolation and clean-slate seeding."""
    client = get_chroma_client(persist_dir)
    try:
        if CHROMA_AVAILABLE and hasattr(client, "delete_collection"):
            client.delete_collection(name=collection_name)
        else:
            client.delete_collection(collection_name)
        return True
    except Exception:
        return False
