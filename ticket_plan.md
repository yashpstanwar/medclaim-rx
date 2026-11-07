# MedClaim Rx — Tracer-Bullet Development Ticket Plan

**Project:** MedClaim Rx — Clinical Prior-Authorization & Formulary Desk  
**Roadmap Scope:** Commits 01 to 68 (Full Implementation, Polish, & Submission Readiness)

---

## 🧭 Dependency Graph

```text
[T-01: Bootstrap & Spec] [x]
        │
        ├──────────────────────┬──────────────────────┐
        ▼                      ▼                      ▼
[T-02: ChromaDB RAG] [x] [T-03: SQLite Registers] [x] [T-04: Labelled Extractor] [x]
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               ▼
                   [T-05: LangGraph Routing] [x]
                               │
                               ▼
                   [T-06: Test Suite & Golden Regression] [x]
                               │
                               ▼
                   [T-07: Streamlit Reviewer UI] [x]
                               │
                               ▼
                   [T-08: Polish, Multi-Tier Governance & Docker] [x]
```

---

## 📋 Ticket Specifications

### [x] T-01: Repository Bootstrap, Environment & Specification Framework
- **Status:** Complete (Day 1)
- **Dependencies:** None
- **Objective:** Establish the foundational Python project structure, Git ignore rules, specification docs, architecture blue-prints, and TypedDict state contract.
- **Key Deliverables:**
  - `README.md`, `.gitignore`, `pyproject.toml`, `.python-version`, `.env.example`
  - `spec.md`, `architecture.md`, `ticket_plan.md`
  - Package directories: `app/`, `eval/`, `tests/`, `data/`, `prompts/`, `issues/`
  - `app/packet.py` (`ClaimPacket` TypedDict)
- **Acceptance Criteria:**
  - [x] Project configuration parses cleanly.
  - [x] Package imports succeed without circular dependencies.

---

### [x] T-02: Clinical Policy RAG & ChromaDB Handbook Strong-Room
- **Status:** Complete (Day 1)
- **Dependencies:** T-01
- **Objective:** Build the institutional knowledge retrieval system using ChromaDB and sentence transformers.
- **Key Deliverables:**
  - `data/clinical_policy.md` (authoritative guidelines)
  - `app/memory.py` (`seed_policy`, `retrieve_policy_chunks`, fail-closed empty shelf protection)
- **Acceptance Criteria:**
  - [x] `seed_policy()` correctly ingests non-heading rule statements.
  - [x] `retrieve_policy_chunks()` returns relevant evidence chunks for queries.
  - [x] Empty collection returns empty list `[]` without unhandled exceptions.

---

### [x] T-03: SQLite Clinical Strong-Room & Parameterized Lookup Tools
- **Status:** Complete (Day 1)
- **Dependencies:** T-01
- **Objective:** Provision ACID-compliant local database for doctor licensure, hospital formulary, and claim audit trails.
- **Key Deliverables:**
  - `app/tools.py` (`get_db_connection`, `seed_db`, `check_license`, `lookup_formulary`, `save_claim`)
  - Auto-seeding of `Dr. Sharma` (`NMC-2019-4410`), `Dr. Verma` (`NMC-2016-8821`), `RX-AMOX-500`, and `RX-ADAL-40`.
- **Acceptance Criteria:**
  - [x] SQL queries use strictly parameterized `?` bindings (no string interpolation).
  - [x] Unregistered `NMC-99INVALID` returns `UNKNOWN`.
  - [x] Formulary lookups return correct status and tier flags (`FOUND:...` on hit, `MISSING` on miss).
  - [x] `save_claim()` persists packet state accurately into `claims` table.

---

### [x] T-04: Deterministic Labelled Rx Extractor & Prompt Specification
- **Status:** Complete (Day 1)
- **Dependencies:** T-01
- **Objective:** Implement deterministic parsing of key-value prescription slips and define prose extraction prompt.
- **Key Deliverables:**
  - `prompts/extract_v1.txt`, `prompts/extract_v2.txt`
  - `app/extract_lab.py` (`parse_labelled` function)
- **Acceptance Criteria:**
  - [x] Accurately strips `₹`, `INR`, commas, and whitespace from currency values.
  - [x] Converts cost to float with 2 decimal precision.
  - [x] Assigns confidence `0.95` when cost is present; assigns `0.40` when cost is missing.
  - [x] Sets prompt_version to `lab_labels_v1`.

---

### [x] T-05: LangGraph Deterministic State Machine & Clinical Gates
- **Status:** Complete (Day 2)
- **Dependencies:** T-02, T-03, T-04
- **Objective:** Wire the functional pipeline into a LangGraph state graph with `extract_node`, `policy_node`, and `route_node`.
- **Key Deliverables:**
  - `app/graph.py` (LangGraph workflow definition, 3 stations)
  - Deterministic evaluation of `COST_GATE` (₹25,000) and `CONF_GATE` (0.80).
  - Explicit routing to `ready_to_dispense` or `needs_pharmacist_review`.
- **Acceptance Criteria:**
  - [x] All routing transitions are deterministic and non-hallucinatory.
  - [x] Audit trace accurately records sequential node execution (`extract` -> `policy` -> `route`).

---

### [x] T-06: Verification Test Suite & Golden Regression Suite
- **Status:** Complete (Day 2)
- **Dependencies:** T-05
- **Objective:** Build unit and integration test coverage across all components, verifying fail-closed assertions and golden benchmarks.
- **Key Deliverables:**
  - `tests/test_packet.py`, `tests/test_extract_lab.py`, `tests/test_tools.py`, `tests/test_memory.py`, `tests/test_log.py`, `tests/test_graph.py`, `tests/test_security.py`
  - `eval/run_golden.py` (5 frozen golden test cases G01-G05)
- **Acceptance Criteria:**
  - [x] 100% pass rate on full test suite.
  - [x] 100% pass rate on Golden Exam runner (`python -m eval.run_golden`).
  - [x] Prompt injection resisted; empty Chroma fails closed.

---

### [x] T-07: Streamlit Clinical Reviewer UI & Audit Dashboard
- **Status:** Complete (Day 2)
- **Dependencies:** T-05, T-06
- **Objective:** Develop an interactive web interface for pharmacy clerks and clinical reviewers.
- **Key Deliverables:**
  - `app/ui.py` (Streamlit interface for prescription input, real-time gate visualization, and audit inspection).
  - `streamlit_app.py` (Cloud deployment entrypoint).
- **Acceptance Criteria:**
  - [x] Provides quick test slip templates (G01 through G06).
  - [x] Displays status badge, station pills, RAG evidence, and JSON trace diary.

---

### [x] T-08: Polish, Multi-Tier Governance, API Gateway & Containerized Deployment
- **Status:** Complete (Polish Sprint)
- **Dependencies:** T-05, T-06, T-07
- **Objective:** Deliver enterprise Polish & Buffer enhancements across routing, governance, observability, REST APIs, and Docker stacks.
- **Key Deliverables:**
  - `app/router.py`: Zero-cost 4-way router and 3-Tier Action Permission Gate.
  - `app/memory.py`: Clinical synonym dictionary and threshold filtering.
  - `app/log.py`: Execution `latency_ms` tracking and comparative token cost receipt.
  - `app/api.py`: FastAPI OpenAPI REST service (`/health`, `/triage`, `/action-gate`).
  - `Dockerfile` & `docker-compose.yml`: Multi-service container orchestration.
  - `app/ui.py`: Persona toggle, Action Gate simulator, and Sequence Flow visualization.
  - `tests/test_router.py`, `tests/test_api.py`: Test suite expanded to 56 passing tests.
- **Acceptance Criteria:**
  - [x] 56 unit tests passing cleanly via `pytest`.
  - [x] Golden Set 100% compliance maintained.
  - [x] Container stack and REST API operational with Swagger documentation.
