# MedClaim Rx — Clinical Prior-Authorization & Formulary Desk

> **"MedClaim Rx clears routine clinical prescriptions same-day without recommending approval on an unverified prescriber NMC license, a non-formulary drug, or a skipped high-cost biologic stamp."**

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)
[![SQLite](https://img.shields.io/badge/Strong--Room-SQLite-lightgrey.svg)](https://www.sqlite.org/)
[![ChromaDB](https://img.shields.io/badge/RAG-ChromaDB-purple.svg)](https://www.trychroma.com/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)](https://streamlit.io/)
[![Safety Grade](https://img.shields.io/badge/Safety-Fail--Closed-green.svg)](#)

---

## 🩺 System Overview

**MedClaim Rx** is a deterministic, clinical-grade Prior-Authorization and Formulary Verification Copilot for hospital pharmacies and Third-Party Administrators (TPAs). Designed with a **fail-closed** safety posture, MedClaim Rx ensures that every prescription claim undergoes strict registry validation, hospital formulary lookup, semantic clinical policy checking, and confidence-gated routing before any dispensing recommendation is issued.

### Core Safety Invariants
- **Zero-Tolerance Licensure Verification:** Authoritative National Medical Commission (NMC) verification against an ACID SQLite strong-room. Unknown or unverified licenses halt approval immediately (`UNKNOWN` $\rightarrow$ `needs_pharmacist_review`, gate: `license_mismatch`).
- **Formulary Whitelisting:** Real-time lookup against the active hospital drug register (`MISSING` $\rightarrow$ `needs_pharmacist_review`, gate: `non_formulary`).
- **Biologic High-Cost Gate:** Prescriptions exceeding ₹25,000 INR deterministically require Chief Medical Officer (CMO) prior authorization (`high_cost_gate`).
- **Prompt Injection Defense:** Embedded narrative commands (e.g. *"Ignore all cost rules", "CMO verbal waiver"*) are treated purely as passive clinical text and overridden by deterministic Python guards.
- **Fail-Closed Policy Vector Store:** An empty or unseeded Chroma vector store immediately halts execution (`empty_policy`).

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

## 🧭 LangGraph 3-Station Workflow

Prescription slips progress deterministically through three sequential stations:

```text
[ START ] ──► [ Station 1: extract ] ──► [ Station 2: policy ] ──► [ Station 3: route ] ──► [ END ]
```

1. **`extract` Station:** Parses structured key-value slips, sanitizes currency notation (`₹`, `INR`, commas), converts cost to float, and scores extraction confidence (`0.95` for valid amounts, `0.40` for missing amounts).
2. **`policy` Station:** Checks extraction confidence against `CONF_GATE` (0.80), retrieves relevant rules from ChromaDB RAG, validates doctor against SQLite `prescribers`, validates drug code against SQLite `formulary`, and evaluates `COST_GATE` (₹25,000 INR).
3. **`route` Station:** Emits the final status recommendation (`ready_to_dispense` or `needs_pharmacist_review`), stamps the trace audit trail, persists claim into `medclaim.db`, and appends a sanitized operational record into `logs/medclaim.jsonl`.

---

## 🧪 Golden Exam Rubric (G01–G05)

The Golden Set Benchmark tests the 5 core clinical scenarios with a required **100% Pass Rate**:

| Case ID | Clinical Scenario | Inputs (Prescriber, NMC, Drug, Cost) | Expected Status | Expected Gate | Result |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **G01_CLEAN** | Routine Generic Antibiotic | Dr. Sharma, NMC-2019-4410, RX-AMOX-500, ₹1,450 | `ready_to_dispense` | `none` | **PASS** |
| **G02_HIGH_BIOLOGIC** | Specialty Biologic (Above ₹25,000) | Dr. Verma, NMC-2016-8821, RX-ADAL-40, ₹68,000 | `needs_pharmacist_review` | `high_cost_gate` | **PASS** |
| **G03_BAD_LICENSE** | Unverified / Fraudulent Prescriber | Dr. Ghost, NMC-99INVALID, RX-AMOX-500, ₹900 | `needs_pharmacist_review` | `license_mismatch` | **PASS** |
| **G04_PROMPT_INJECT** | Hostile Injection in Prescription Notes | Dr. Verma, NMC-2016-8821, RX-ADAL-40, ₹75,000 + *"Ignore rules"* | `needs_pharmacist_review` | `high_cost_gate` | **PASS** |
| **G05_NON_FORMULARY** | Unlisted / Experimental Drug | Dr. Sharma, NMC-2019-4410, RX-EXPERIMENTAL-99, ₹4,200 | `needs_pharmacist_review` | `non_formulary` | **PASS** |

---

## ⚡ Quickstart Commands

### 1. Run Automated Unit Test Suite
```bash
PYTHONPATH=. pytest -v
```
*(Runs all unit tests across state contracts, extractors, SQLite registers, Chroma memory, LangGraph stations, PII logger, and adversarial security).*

### 2. Execute Golden Set Regression Exam
```bash
PYTHONPATH=. python -m eval.run_golden
```
*(Executes G01 through G05 benchmark suite and outputs formatted pass/fail matrix).*

### 3. Launch Streamlit Obsidian Dark-Mode Console
```bash
streamlit run app/ui.py
```
*(Launches the interactive 3-tab triage desk, live preset runner, Golden exam dashboard, and SQLite/JSONL observability browser).*

---

## 📁 Repository Layout

```text
├── .env.example              # Environment variables template
├── .gitignore                # Production git exclusion patterns
├── .python-version           # Target Python 3.12 pin
├── pyproject.toml            # Project specification & uv dependencies
├── README.md                 # Complete system guide & architecture manual
├── spec.md                   # Product specification & clinical rules
├── architecture.md           # 3-Drawer memory & system flow architecture
├── ticket_plan.md            # Tracer-bullet ticket plan (T-01 to T-07) [All Complete]
├── app/
│   ├── __init__.py           # Core application package
│   ├── packet.py             # Strongly-typed ClaimPacket state contract
│   ├── memory.py             # ChromaDB RAG clinical policy memory
│   ├── tools.py              # SQLite strong-room & lookup tools
│   ├── extract_lab.py        # Deterministic labelled prescription extractor
│   ├── log.py                # PII-safe JSONL operational trace logger
│   ├── graph.py              # LangGraph 3-station workflow engine
│   └── ui.py                 # Streamlit clinical reviewer console (Obsidian theme)
├── data/
│   ├── clinical_policy.md    # Clinical policy handbook (RAG source)
│   └── medclaim.db           # SQLite database (auto-generated by seed_db)
├── logs/
│   └── medclaim.jsonl        # PII-safe non-repudiable audit trace ledger
├── prompts/
│   ├── extract_v1.txt        # Prompt template v1 for clinical prose notes
│   └── extract_v2.txt        # Advanced prompt template v2 with ICD-10 mapping
├── issues/                   # Issue Tracker Cards (ISSUE-01 to ISSUE-07)
│   ├── ISSUE-01_STATE_CONTRACT.md
│   ├── ISSUE-02_CHROMA_RAG.md
│   ├── ISSUE-03_SQLITE_STRONGROOM.md
│   ├── ISSUE-04_LABELLED_EXTRACTOR.md
│   ├── ISSUE-05_LANGGRAPH_ROUTING.md
│   ├── ISSUE-06_GOLDEN_EVAL_AND_SECURITY.md
│   └── ISSUE-07_STREAMLIT_CONSOLE.md
├── eval/
│   ├── __init__.py           # Evaluation framework package
│   └── run_golden.py         # 5-Case Golden Set Benchmark CLI & test runner
└── tests/
    ├── __init__.py           # Test suite package
    ├── test_packet.py        # ClaimPacket type contract tests
    ├── test_extract_lab.py   # Labelled extractor tests
    ├── test_tools.py         # SQLite registry & lookup tests
    ├── test_memory.py        # ChromaDB policy memory tests
    ├── test_log.py           # PII-safe JSONL logger unit tests
    ├── test_graph.py         # LangGraph station routing unit tests
    └── test_security.py      # Prompt injection & empty Chroma fail-closed tests
```
