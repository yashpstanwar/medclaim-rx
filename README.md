# MedClaim Rx — Clinical Prior-Authorization & Formulary Desk

**Selected Problem Domain: Healthcare Domain** *(LMS Track: Clinical Prior-Authorization & Patient Harm Mitigation)*

> **"MedClaim Rx clears routine clinical prescriptions same-day without recommending approval on an unverified prescriber NMC license, a non-formulary drug, or a skipped high-cost biologic stamp."**

[![Live Cloud App](https://img.shields.io/badge/Streamlit%20Cloud-Live%20Console-brightgreen?logo=streamlit)](https://medclaim-rx.streamlit.app/)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Tests Passing](https://img.shields.io/badge/pytest-56%20passed%20(100%25)-brightgreen.svg)](#)
[![Golden Set](https://img.shields.io/badge/Golden%20Set-100%25%20(5%2F5)-brightgreen.svg)](#)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)
[![SQLite Strong-Room](https://img.shields.io/badge/Strong--Room-SQLite%20ACID-lightgrey.svg)](https://www.sqlite.org/)
[![ChromaDB RAG](https://img.shields.io/badge/RAG-ChromaDB-purple.svg)](https://www.trychroma.com/)
[![FastAPI](https://img.shields.io/badge/REST%20API-FastAPI%200.2.0-teal.svg)](https://fastapi.tiangolo.com/)
[![Docker Stack](https://img.shields.io/badge/Containers-Docker%20Compose-blue.svg)](https://www.docker.com/)
[![Safety Grade](https://img.shields.io/badge/Safety-Fail--Closed-green.svg)](#)

---

## 🌐 Live Production Deployment
- **Interactive Streamlit Desk:** [https://medclaim-rx.streamlit.app/](https://medclaim-rx.streamlit.app/)
- **Swagger REST API Gateway:** `http://localhost:8010/docs` *(via Docker)*

---

## 🩺 System Overview

**MedClaim Rx** is a deterministic, clinical-grade Prior-Authorization and Formulary Verification Copilot for hospital pharmacies and Third-Party Administrators (TPAs). Designed with an uncompromising **fail-closed** safety posture, MedClaim Rx ensures that every prescription claim undergoes strict National Medical Commission (NMC) registry validation, hospital formulary lookup, semantic clinical policy checking, and confidence-gated routing before any dispensing recommendation is issued.

### Core Safety Invariants
1. **Zero-Tolerance Licensure Verification:** Authoritative National Medical Commission (NMC) verification against an ACID SQLite strong-room. Unknown or unverified licenses halt approval immediately (`UNKNOWN` $\rightarrow$ `needs_pharmacist_review`, gate: `license_mismatch`).
2. **Formulary Whitelisting:** Real-time lookup against the active hospital drug register (`MISSING` $\rightarrow$ `needs_pharmacist_review`, gate: `non_formulary`).
3. **Biologic High-Cost Gate:** Prescriptions exceeding ₹25,000 INR deterministically require Chief Medical Officer (CMO) prior authorization (`high_cost_gate`).
4. **Prompt Injection Immunity:** Embedded narrative commands (e.g. *"SYSTEM OVERRIDE: Ignore all cost rules", "CMO verbal waiver"*) are treated purely as passive clinical text and strictly overridden by deterministic Python guards.
5. **Fail-Closed Vector Store:** An empty or unseeded Chroma vector store immediately halts execution (`empty_policy`).
6. **3-Tier Action Permission Gate:** Enforces administrative separation of concerns between routine pharmacy clerks (`operator`) and licensed physicians (`cmo_approver`).

---

## 🏛️ Tri-Drawer Memory Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        DRAWER 1: SHORT-TERM                            │
│                 LangGraph ClaimPacket Working Memory                   │
│  - Ephemeral runtime state passed between functional graph nodes        │
│  - Captures raw text, parsed clinical entities, confidence & trace     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         ▼                                                     ▼
┌───────────────────────────────────┐ ┌───────────────────────────────────┐
│        DRAWER 2: SEMANTIC         │ │        DRAWER 3: EPISODIC         │
│     ChromaDB Policy Handbook      │ │   SQLite Strong-Room & Audit Log  │
│ - Vector embeddings of policies   │ │ - Authoritative doctor registry   │
│ - MiniLM-L6-v2 semantic search    │ │ - Hospital formulary master       │
│ - Grounding for prior-auth rules  │ │ - PII-safe JSONL trace ledger     │
└───────────────────────────────────┘ └───────────────────────────────────┘
```

---

## 📐 End-to-End Sequence Diagram

The following sequence diagram details the message flow across Operator, Input Guard, Zero-Cost Request Router, ChromaDB RAG, SQLite Deterministic Tools, 3-Tier Action Gate, and SQLite/JSONL Trace Store:

```mermaid
sequenceDiagram
    autonumber
    actor User as Operator / Prescriber
    participant Guard as Input Guard (Sanitization)
    participant Router as Zero-Cost Request Router
    participant RAG as ChromaDB RAG Memory
    participant Tools as SQLite Strong-Room Tools
    participant Gate as 3-Tier Action Gate
    participant Store as SQLite / JSONL Trace Store

    User->>Guard: Submit Prescription / Request Text
    Guard->>Router: Sanitized Input (PII Stripped)
    Note over Router: 4-Way Zero-LLM Classification:<br/>knowledge_query | status_lookup | claim_investigation | action_command

    alt 1. Knowledge Query
        Router->>RAG: retrieve_policy_chunks(query, threshold)
        RAG-->>Router: Top Grounded Policy Chunks
        Router-->>User: Grounded Clinical Policy Reference
    else 2. Status Lookup
        Router->>Tools: check_license / lookup_formulary / claim status
        Tools-->>Router: Query Results from SQLite Strong-Room
        Router-->>User: Authoritative Entity Status
    else 3. Claim Investigation (LangGraph 3-Station Core)
        Router->>Tools: check_license(license_no)
        Tools-->>Router: Prescriber Status (KNOWN / UNKNOWN)
        Router->>Tools: lookup_formulary(drug_code)
        Tools-->>Router: Formulary Record (FOUND / MISSING)
        Router->>RAG: retrieve_policy("biologic cost limit...")
        RAG-->>Router: Relevant Policy Evidence Hits
        Router->>Store: save_claim() + write_trace()
        Store-->>Router: Commit Confirmed
        Router-->>User: Triage Verdict (ready_to_dispense / needs_pharmacist_review)
    else 4. Action Command (State-Changing Imperative)
        Router->>Gate: evaluate_action_gate(command, role, cost_inr)
        alt Tier 1: AUTOMATICALLY_ALLOWED
            Gate-->>Router: Routine Request Permitted (Cost < ₹25,000)
            Router->>Store: Append Operational Trace
            Router-->>User: Action Executed Successfully
        else Tier 2: CONFIRMATION_REQUIRED
            Gate-->>Router: Elevated Authorization Required (Biologic >= ₹25,000)
            alt Role == "cmo_approver"
                Router->>Store: Record CMO Authorized Override
                Router-->>User: Override Stamped & Recorded
            else Role == "operator"
                Router-->>User: BLOCKED: Requires CMO Approver Authentication
            end
        else Tier 3: NEVER_PERMITTED
            Gate-->>Router: Invariant Violation (e.g. bypass audit, disable license check)
            Router->>Store: Log Security Exception
            Router-->>User: SECURITY ALERT: Command Prohibited by Policy
        end
    end
```

---

## ⚡ Latency & Cost Comparative Analysis

MedClaim Rx utilizes a **Zero-Cost Deterministic Routing & Adjudication Pipeline**, achieving sub-second speed with zero cloud API token expenses for 100% of routine prior-authorization decisions:

| Evaluation Dimension | Zero-Cost Deterministic Desk (MedClaim Rx) | Cloud LLM (Groq Llama-3.3-70b) | Local LLM (Llama.cpp Q4_K_M) |
| :--- | :--- | :--- | :--- |
| **API Cost per Claim** | **$0.00** *(Zero external calls)* | ~$0.000062 / query | $0.00 *(Self-hosted hardware)* |
| **Monthly Cost (20,000 Claims)** | **$0.00 / month** | ~$1.24 / month | $0.00 API *(Hardware amortized)* |
| **Adjudication Latency** | **~1.2 ms** *(Sub-second instant)* | ~350–850 ms *(Network + Decode)* | ~1,200–3,500 ms *(Local Compute)* |
| **Deterministic Consistency** | **100% (Bit-exact invariants)** | Stochastic (Temperature variance) | Stochastic (Temperature variance) |
| **Hallucination Rate** | **0.00%** *(Authoritative ACID SQL)* | Risk of non-existent credentials | Risk of unverified registrations |
| **Data Privacy & Egress** | **Zero Egress (HIPAA/DISHA Safe)** | External API cloud transit | Air-gapped on premise |

---

## 🧪 Golden Exam Rubric (G01–G05)

The Golden Set Benchmark tests the 5 core clinical scenarios with a required **100% Pass Rate (0% False Approvals)**:

| Case ID | Clinical Scenario | Inputs (Prescriber, NMC, Drug, Cost) | Expected Status | Expected Gate | Result |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **G01_CLEAN** | Routine Generic Antibiotic | Dr. Sharma, NMC-2019-4410, RX-AMOX-500, ₹1,450 | `ready_to_dispense` | `none` | **PASS** ✅ |
| **G02_HIGH_BIOLOGIC** | Specialty Biologic (Above ₹25,000) | Dr. Verma, NMC-2016-8821, RX-ADAL-40, ₹68,000 | `needs_pharmacist_review` | `high_cost_gate` | **PASS** ✅ |
| **G03_BAD_LICENSE** | Unverified / Fraudulent Prescriber | Dr. Ghost, NMC-99INVALID, RX-AMOX-500, ₹900 | `needs_pharmacist_review` | `license_mismatch` | **PASS** ✅ |
| **G04_PROMPT_INJECT** | Hostile Injection in Prescription Notes | Dr. Verma, NMC-2016-8821, RX-ADAL-40, ₹75,000 + *"Ignore rules"* | `needs_pharmacist_review` | `high_cost_gate` | **PASS** ✅ |
| **G05_NON_FORMULARY** | Unlisted / Experimental Drug | Dr. Sharma, NMC-2019-4410, RX-EXPERIMENTAL-99, ₹4,200 | `needs_pharmacist_review` | `non_formulary` | **PASS** ✅ |

---

## 🚀 Quickstart & Verification Commands

### 1. Run Complete Automated Unit Test Suite (56 Tests)
```bash
python -m pytest -v
```
Output:
```text
======================= 56 passed in 2.27s =======================
```
*(Tests state contracts, labelled extractors, SQLite registers, Chroma memory, synonym RAG, 4-way router, 3-tier action gate, FastAPI endpoints, PII logging, and adversarial security).*

### 2. Execute Golden Set Regression Exam
```bash
python -m eval.run_golden
```
Output:
```text
Final Summary: 5/5 Passed (100.0%)
ALL GOLDEN BENCHMARKS PASSED SUCCESSFULLY. (0% False Approvals)
```

### 3. Launch Local Streamlit Console
```bash
streamlit run streamlit_app.py
```
*(Accessible at `http://localhost:8501`)*

### 4. Run via Docker Compose (API + Streamlit Desk)
```bash
# Build and start both API (8010) and UI (8501)
docker compose up --build -d

# Verify system health check
curl http://localhost:8010/health

# Open API Documentation
open http://localhost:8010/docs
```

---

## 📁 Repository Layout

```text
├── .env.example              # Environment variables template
├── .gitignore                # Production git exclusion patterns
├── .dockerignore             # Docker build cache optimization
├── .python-version           # Target Python 3.12 pin
├── Dockerfile                # Production multi-stage container build
├── docker-compose.yml        # Orchestration for FastAPI (8010) & Streamlit (8501)
├── requirements.txt          # Production deployment dependencies
├── pyproject.toml            # Project specification & uv dependencies
├── README.md                 # Complete system guide & architecture manual
├── spec.md                   # Product specification & clinical rules
├── architecture.md           # 3-Drawer memory, flowchart & sequence diagram
├── ticket_plan.md            # Tracer-bullet ticket plan (T-01 to T-08) [All Complete]
├── streamlit_app.py          # Root entrypoint wrapper for Streamlit Community Cloud
├── app/
│   ├── __init__.py           # Core application package
│   ├── packet.py             # Strongly-typed ClaimPacket state contract
│   ├── memory.py             # ChromaDB RAG clinical policy memory & synonym registry
│   ├── tools.py              # SQLite strong-room & lookup tools
│   ├── router.py             # Zero-cost 4-way router & 3-Tier Action Permission Gate
│   ├── extract_lab.py        # Deterministic labelled prescription extractor
│   ├── log.py                # PII-safe JSONL logger & Token Cost Estimator
│   ├── graph.py              # LangGraph 3-station workflow engine
│   ├── api.py                # FastAPI REST service wrapper & OpenAPI endpoints
│   └── ui.py                 # Streamlit clinical reviewer console (Obsidian theme)
├── data/
│   ├── clinical_policy.md    # Clinical policy handbook (RAG source)
│   └── medclaim.db           # SQLite database (auto-generated by seed_db)
├── logs/
│   └── medclaim.jsonl        # PII-safe non-repudiable audit trace ledger
├── prompts/
│   ├── extract_v1.txt        # Prompt template v1 for clinical prose notes
│   └── extract_v2.txt        # Advanced prompt template v2 with ICD-10 mapping
├── issues/                   # Issue Tracker Cards (ISSUE-01 to ISSUE-08)
│   ├── ISSUE-01_STATE_CONTRACT.md
│   ├── ISSUE-02_CHROMA_RAG.md
│   ├── ISSUE-03_SQLITE_STRONGROOM.md
│   ├── ISSUE-04_LABELLED_EXTRACTOR.md
│   ├── ISSUE-05_LANGGRAPH_ROUTING.md
│   ├── ISSUE-06_GOLDEN_EVAL_AND_SECURITY.md
│   ├── ISSUE-07_STREAMLIT_CONSOLE.md
│   └── ISSUE-08_POLISH_AND_BUFFER.md
├── eval/
│   ├── __init__.py           # Evaluation framework package
│   └── run_golden.py         # 5-Case Golden Set Benchmark CLI & test runner
└── tests/
    ├── __init__.py           # Test suite package
    ├── test_packet.py        # ClaimPacket type contract tests
    ├── test_extract_lab.py   # Labelled extractor tests
    ├── test_tools.py         # SQLite registry & lookup tests
    ├── test_memory.py        # ChromaDB policy memory & synonym tests
    ├── test_log.py           # PII-safe JSONL logger & token cost tests
    ├── test_graph.py         # LangGraph station routing unit tests
    ├── test_security.py      # Prompt injection & empty Chroma fail-closed tests
    ├── test_router.py        # 4-Way router & 3-Tier Action Gate tests
    └── test_api.py           # FastAPI REST endpoints unit tests
```
