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
ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_COLLECTION_NAME = "clinical_policies"
DEFAULT_CHROMA_DIR = str(ROOT_DIR / ".chroma")
DEFAULT_POLICY_PATH = str(ROOT_DIR / "data" / "clinical_policy.md")

# Similarity Threshold Tuning
DEFAULT_THRESHOLD: float = 0.40
STRICT_THRESHOLD: float = 0.17

# Clinical Domain Synonym Registry (Bidirectional clinical expansion)
CLINICAL_SYNONYMS: dict[str, list[str]] = {
    "biologic": ["adalimumab", "restricted", "high-cost", "immunosuppressive"],
    "biologics": ["adalimumab", "restricted", "high-cost", "immunosuppressive"],
    "adalimumab": ["biologic", "biologics", "restricted", "high-cost"],
    "license": ["nmc", "registration", "prescriber", "credential"],
    "licensure": ["nmc", "registration", "prescriber", "credential"],
    "stamp": ["approval", "cmo", "override", "prior-auth"],
    "cmo": ["stamp", "approval", "override", "prior-auth"],
    "formulary": ["whitelisted", "approved", "tier", "catalog"],
    "antibiotic": ["amoxicillin", "anti-infective", "routine"],
    "amoxicillin": ["antibiotic", "routine", "anti-infective"],
    "doctor": ["physician", "practitioner", "prescriber", "nmc"],
}


def expand_query_synonyms(query: str) -> str:
    """Expand clinical terms in query with domain synonyms to improve RAG recall.

    Examples:
      - 'biologic' -> 'biologic adalimumab restricted high-cost immunosuppressive'
      - 'license' -> 'license nmc registration prescriber credential'
      - 'stamp' -> 'stamp approval cmo override prior-auth'
    """
    if not query or not query.strip():
        return query

    tokens = re.findall(r"\w+", query.lower())
    additions: list[str] = []
    for token in tokens:
        if token in CLINICAL_SYNONYMS:
            for syn in CLINICAL_SYNONYMS[token]:
                if syn not in tokens and syn not in additions:
                    additions.append(syn)

    if additions:
        return f"{query} {' '.join(additions)}"
    return query


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
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 3,
        threshold: Optional[float] = None,
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
            if threshold is not None:
                if score >= threshold:
                    scored.append((score, it["document"]))
            else:
                if score > 0:
                    scored.append((score, it["document"]))

        scored.sort(key=lambda x: x[0], reverse=True)
        if threshold is not None:
            return [doc for score, doc in scored[:n_results]]
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


def policy_collection(persist_dir: str = DEFAULT_CHROMA_DIR, collection_name: str = DEFAULT_COLLECTION_NAME):
    """Retrieve ChromaDB collection or fallback store."""
    client = get_chroma_client(persist_dir)
    if hasattr(client, "get_or_create_collection"):
        emb_fn = get_embedding_function()
        if emb_fn:
            return client.get_or_create_collection(name=collection_name, embedding_function=emb_fn)
        return client.get_or_create_collection(name=collection_name)
    return client.get_or_create_collection(collection_name)


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
    threshold: Optional[float] = None,
    expand_synonyms: bool = True,
) -> List[str]:
    """Retrieve top relevant clinical policy chunks from Chroma vector index.

    Enforces fail-closed behavior: returns [] if collection is empty or missing.
    Supports clinical synonym expansion and similarity threshold filtering.

    Args:
        query: Clinical search query (e.g. 'biologic cost limit').
        n_results: Maximum number of chunks to return.
        persist_dir: Chroma persistent directory.
        collection_name: Target Chroma collection name.
        threshold: Minimum similarity threshold (e.g. DEFAULT_THRESHOLD or STRICT_THRESHOLD).
        expand_synonyms: Whether to expand query with CLINICAL_SYNONYMS.

    Returns:
        List of matching policy rule strings, or [] if empty/fail-closed.
    """
    search_query = expand_query_synonyms(query) if expand_synonyms else query
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
                query_texts=[search_query],
                n_results=min(n_results, collection.count()),
                include=["documents", "distances"],
            )
            docs = results.get("documents", [])
            distances = results.get("distances", [])
            if docs and len(docs) > 0:
                doc_list = docs[0]
                dist_list = distances[0] if distances and len(distances) > 0 else []
                if threshold is not None and dist_list:
                    filtered = []
                    for doc, dist in zip(doc_list, dist_list):
                        sim = 1.0 - min(float(dist), 1.0)
                        if sim >= threshold:
                            filtered.append(doc)
                    return filtered
                return doc_list
            return []
        except Exception:
            # On vector error, fail-closed
            return []
    else:
        store = _get_fallback_store(persist_dir)
        if store.count(collection_name) == 0:
            return []
        return store.query(
            collection_name=collection_name,
            query_text=search_query,
            n_results=n_results,
            threshold=threshold,
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
