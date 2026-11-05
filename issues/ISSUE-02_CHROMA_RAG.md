# Issue #02: ChromaDB Clinical Policy RAG Handbook

**Label:** `rag` `chromadb` `policy-engine`  
**Milestone:** Day 1 Foundation  
**Assignee:** Core Backend Agent  

---

## 📌 Context
Clinical guidelines evolve and contain nuanced conditions (e.g. high-cost biologic stamps, emergency substitutes, off-label prior authorization). These guidelines must be maintained in human-readable Markdown (`data/clinical_policy.md`) and vectorized in a persistent ChromaDB store for real-time semantic retrieval.

## 🎯 Requirements
1. Implement `app/memory.py` utilizing persistent ChromaDB storage (`.chroma/`).
2. Use embedding model `sentence-transformers/all-MiniLM-L6-v2`.
3. Provide `seed_policy(policy_path: str, collection_name: str)` function:
   - Reads `clinical_policy.md`.
   - Filters out markdown headings and blank lines.
   - Upserts each discrete policy rule into Chroma with deterministic IDs.
4. Provide `retrieve_policy_chunks(query: str, n_results: int = 3)`:
   - Queries top matching semantic chunks based on query string.
5. **Fail-Closed Protection:**
   - If the collection is unseeded or empty, return an empty list `[]` without raising unhandled exceptions, enabling downstream nodes to fail-closed (`POLICY_ENGINE_UNAVAILABLE`).

## ✅ Acceptance Criteria
- Policy seeding idempotently upserts rules without duplicate bloat.
- Semantic query for "biologic cost limit" returns the ₹25,000 threshold chunk.
- Querying against empty or unseeded collection safely returns `[]`.
