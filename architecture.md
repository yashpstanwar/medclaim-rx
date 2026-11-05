# MedClaim Rx — Architecture & Memory Specification

**System:** MedClaim Rx — Clinical Prior-Authorization & Formulary Desk  
**Architecture Pattern:** Tri-Drawer Memory Model + Deterministic State Machine  
**Safety Grade:** Clinical Fail-Closed

---

## 1. High-Level Architectural Overview

MedClaim Rx combines deterministic Python gating, relational verification registers, and semantic vector retrieval within an event-driven LangGraph state workflow. By decoupling unstructured natural language interpretation from immutable relational registries, the system ensures that AI cannot hallucinate physician credentials, bypass hospital formularies, or skip high-cost approvals.

---

## 2. Tri-Drawer Memory Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        DRAWER 1: SHORT-TERM                            │
│                 LangGraph ClaimPacket Working Memory                   │
│  - Ephemeral runtime state passed between functional graph nodes        │
│  - Captures raw text, parsed clinical entities, confidence & trace    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         ▼                                                     ▼
┌───────────────────────────────────┐ ┌───────────────────────────────────┐
│        DRAWER 2: SEMANTIC         │ │        DRAWER 3: EPISODIC         │
│     ChromaDB Policy Handbook      │ │   SQLite Strong-Room & Audit Log  │
│ - Vector embeddings of policies   │ │ - Authoritative doctor registry   │
│ - MiniLM-L6-v2 semantic search    │ │ - Hospital formulary master       │
│ - Grounding for prior-auth rules  │ │ - Immutable claims audit ledger   │
└───────────────────────────────────┘ └───────────────────────────────────┘
```

### Drawer 1: Short-Term Working State (`ClaimPacket`)
- **Scope:** In-flight claim lifecycle.
- **Technology:** Python `TypedDict` managed by LangGraph state channels.
- **Contents:** Cleaned clinical parameters (`drug_code`, `cost_inr`, `license_no`), extraction confidence score, execution trace breadcrumbs, and real-time gating flags.
- **Persistence:** Volatile during computation; finalized state is written to Drawer 3 upon completion.

### Drawer 2: Semantic Institutional Memory (ChromaDB)
- **Scope:** Clinical Prior-Authorization & Formulary Guidelines.
- **Technology:** Persistent ChromaDB collection (`.chroma/`) embedded via `sentence-transformers/all-MiniLM-L6-v2`.
- **Contents:** Vectorized policy clauses derived from `data/clinical_policy.md` (e.g. biologic limits, step therapy requirements, off-label prior-auth criteria).
- **Fail-Closed Rule:** If the Chroma shelf is empty or unreachable, the system halts with `POLICY_ENGINE_UNAVAILABLE` rather than defaulting to approval.

### Drawer 3: Episodic Long-Term Strong-Room (SQLite & JSONL)
- **Scope:** Immutable records of authority, formulary truth, and historical adjudications.
- **Technology:** ACID-compliant SQLite (`data/medclaim.db`) with `sqlite3.Row` factory, alongside append-only JSONL audit logs (`logs/audit_traces.jsonl`).
- **Contents:**
  1. `prescribers`: Authoritative NMC doctor license status.
  2. `formulary`: Whitelisted hospital drug codes, therapeutic classes, and pricing tiers.
  3. `claims`: Historical adjudication records with gate outcomes and timestamps.
