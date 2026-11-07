# ISSUE-08: Polish, Multi-Tier Governance, API Gateway & Containerized Deployment

**Status:** Completed  
**Sprint:** Polish & Buffer / Submission Readiness  
**Target Delivery:** Lecture Polish Milestone  

---

## 1. Problem Statement & Scope

MedClaim Rx requires enterprise-grade submission polish, deterministic cost guarantees, formal API exposure, containerized reproducibility, and multi-tier role governance. This issue governs the implementation of:
1. **Mermaid Sequence Diagram:** Formalizing the end-to-end message flow across Operator, Input Guard, Router, ChromaDB RAG, SQLite Strong-Room, 3-Tier Action Gate, and JSONL Trace Store.
2. **Clinical Synonym Expansion & RAG Threshold Tuning:** Bidirectional synonym dictionary (`CLINICAL_SYNONYMS`) covering biologics, licenses, stamps, and formulary terms with configurable thresholds (`DEFAULT_THRESHOLD = 0.40`, `STRICT_THRESHOLD = 0.17`).
3. **Zero-Cost 4-Way Request Router:** Deterministic, zero-LLM-cost router classifying inputs into `knowledge_query`, `status_lookup`, `claim_investigation`, or `action_command`.
4. **3-Tier Action Permission Gate:**
   - **Tier 1 (AUTOMATICALLY_ALLOWED):** Low-risk standard queries and routine clearances (< ₹25,000).
   - **Tier 2 (CONFIRMATION_REQUIRED):** High-cost biologics (≥ ₹25,000) or manual overrides; requires `role == "cmo_approver"`.
   - **Tier 3 (NEVER_PERMITTED):** Hard blocks for safety invariant violations (e.g. bypass audit log, disable license gate).
5. **Observability & Token Cost Receipt:** Measuring `latency_ms` via `time.perf_counter()` and comparing Zero-Cost Deterministic ($0.00) vs. Groq API (~$0.06–$1.24/mo scale) vs. Local Llama.cpp ($0.00).
6. **FastAPI REST Gateway (`app/api.py`):** Exposing `/health`, `/triage`, and `/action-gate` with explicit silent-failure guards and Swagger docs.
7. **Containerization:** Production `Dockerfile` and `docker-compose.yml` orchestrating API (port 8010) and UI (port 8501).
8. **UI Polish & Interactive Simulator:** Sidebar persona switcher (Operator vs. CMO Approver), action gate tester, latency metrics, and Sequence Flow tab in `app/ui.py`.

---

## 2. Technical Architecture & Invariants

```text
[Incoming Slip / Command]
          │
          ▼
 [Input Guard Sanitizer] (Strips PII)
          │
          ▼
 [Zero-Cost 4-Way Router]
    ├─► knowledge_query    ──► ChromaDB RAG + Synonym Expansion (Threshold Tuned)
    ├─► status_lookup      ──► SQLite Strong-Room Queries (Prescribers / Formulary / Claims)
    ├─► claim_investigation──► LangGraph 3-Station Core (Extract -> Policy -> Route)
    └─► action_command     ──► 3-Tier Action Permission Gate (Operator vs. CMO Approver)
```

### Safety Invariants:
- Zero LLM inference cost on routing and standard rule adjudication.
- Never write patient names, Aadhaar identifiers, or raw clinical prose to persistent disk.
- Empty policy index or unseeded database must fail-closed.
- Tier 3 invariant-violating commands are prohibited regardless of user role.

---

## 3. Verification & Acceptance Criteria

- [x] Full pytest suite passes with 56 passing unit tests (`tests/test_router.py`, `tests/test_api.py`, `tests/test_memory.py`, `tests/test_log.py`).
- [x] All 5 Golden Benchmark cases (G01–G05) pass with 100% compliance (`python -m eval.run_golden`).
- [x] Dockerfile and Docker Compose build cleanly and map ports 8010 and 8501.
- [x] Swagger docs accessible at `http://localhost:8010/docs`.
- [x] Streamlit Cloud root wrapper (`streamlit_app.py`) functions with zero import errors.
