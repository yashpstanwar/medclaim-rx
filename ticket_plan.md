# MedClaim Rx — Tracer-Bullet Development Ticket Plan

**Project:** MedClaim Rx — Clinical Prior-Authorization & Formulary Desk  
**Roadmap Scope:** Commits 01 to 28 (Day 1 Execution and Foundation)

---

## 🧭 Dependency Graph

```text
[T-01: Bootstrap & Spec]
        │
        ├──────────────────────┬──────────────────────┐
        ▼                      ▼                      ▼
[T-02: ChromaDB RAG]   [T-03: SQLite Registers]   [T-04: Labelled Extractor]
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               ▼
                   [T-05: LangGraph Routing]
                               │
                               ▼
                   [T-06: Test Suite & Regression]
                               │
                               ▼
                   [T-07: Streamlit Reviewer UI]
```

---

## 📋 Ticket Specifications

### T-01: Repository Bootstrap, Environment & Specification Framework
- **Status:** In Progress (Day 1)
- **Dependencies:** None
- **Objective:** Establish the foundational Python project structure, Git ignore rules, specification docs, architecture blue-prints, and TypedDict state contract.
- **Key Deliverables:**
  - `README.md`, `.gitignore`, `pyproject.toml`, `.python-version`, `.env.example`
  - `spec.md`, `architecture.md`, `ticket_plan.md`
  - Package directories: `app/`, `eval/`, `tests/`, `data/`, `prompts/`, `issues/`
  - `app/packet.py` (`ClaimPacket` TypedDict)
- **Acceptance Criteria:**
  - Project configuration parses cleanly.
  - Package imports succeed without circular dependencies.

---

### T-02: Clinical Policy RAG & ChromaDB Handbook Strong-Room
- **Status:** In Progress (Day 1)
- **Dependencies:** T-01
- **Objective:** Build the institutional knowledge retrieval system using ChromaDB and sentence transformers.
- **Key Deliverables:**
  - `data/clinical_policy.md` (authoritative guidelines)
  - `app/memory.py` (`seed_policy`, `retrieve_policy_chunks`, fail-closed empty shelf protection)
- **Acceptance Criteria:**
  - `seed_policy()` correctly ingests non-heading rule statements.
  - `retrieve_policy_chunks()` returns relevant evidence chunks for queries like "high cost biologic authorization".
  - Empty collection returns empty list `[]` without unhandled exceptions.

---

### T-03: SQLite Clinical Strong-Room & Parameterized Lookup Tools
- **Status:** In Progress (Day 1)
- **Dependencies:** T-01
- **Objective:** Provision ACID-compliant local database for doctor licensure, hospital formulary, and claim audit trails.
- **Key Deliverables:**
  - `app/tools.py` (`get_db_connection`, `seed_db`, `check_license`, `lookup_formulary`, `save_claim`)
  - Auto-seeding of `Dr. Sharma` (`NMC-2019-4410`), `Dr. Verma` (`NMC-2016-8821`), `RX-AMOX-500`, and `RX-ADAL-40`.
- **Acceptance Criteria:**
  - SQL queries use strictly parameterized `?` bindings (no string interpolation).
  - Unregistered `NMC-99INVALID` returns `None`.
  - Formulary lookups return correct status and tier flags.
  - `save_claim()` persists packet state accurately into `claims` table.

---

### T-04: Deterministic Labelled Rx Extractor & Prompt Specification
- **Status:** In Progress (Day 1)
- **Dependencies:** T-01
- **Objective:** Implement deterministic parsing of key-value prescription slips and define prose extraction prompt.
- **Key Deliverables:**
  - `prompts/extract_v1.txt` (structured JSON extraction instructions with anti-injection defenses)
  - `app/extract_lab.py` (`parse_labelled` function)
- **Acceptance Criteria:**
  - Accurately strips `₹`, `INR`, commas, and whitespace from currency values.
  - Converts cost to float with 2 decimal precision.
  - Assigns confidence `0.95` when cost is present; assigns `0.40` when cost is missing.
  - Tolerates alternate key names (`Prescriber:`, `Doctor:`, `Cost:`, `Amount:`, `Rx:`).

---

### T-05: LangGraph Deterministic State Machine & Clinical Gates
- **Status:** Planned
- **Dependencies:** T-02, T-03, T-04
- **Objective:** Wire the functional pipeline into a LangGraph state graph with `extract_node`, `policy_node`, and `route_node`.
- **Key Deliverables:**
  - `app/graph.py` (LangGraph workflow definition)
  - Deterministic evaluation of `COST_GATE` (₹25,000) and `CONF_GATE` (0.80).
  - Explicit routing to `ready_to_dispense`, `cmo_review_needed`, `pharmacist_review_needed`, or `rejected_invalid`.
- **Acceptance Criteria:**
  - All routing transitions are deterministic and non-hallucinatory.
  - Audit trace accurately records sequential node execution.

---

### T-06: Verification Test Suite & Fail-Closed Regression Assertions
- **Status:** In Progress / Continuous
- **Dependencies:** T-05
- **Objective:** Build unit and integration test coverage across all components, verifying fail-closed assertions.
- **Key Deliverables:**
  - `tests/test_packet.py`, `tests/test_extract_lab.py`, `tests/test_tools.py`, `tests/test_memory.py`, `tests/test_graph.py`
- **Acceptance Criteria:**
  - 100% pass rate on test suite.
  - High-cost biologic slips route to CMO review.
  - Unregistered doctor slips route to invalid rejection.

---

### T-07: Streamlit Clinical Reviewer UI & Audit Dashboard
- **Status:** Planned
- **Dependencies:** T-05, T-06
- **Objective:** Develop an interactive web interface for pharmacy clerks and clinical reviewers.
- **Key Deliverables:**
  - `app/ui.py` (Streamlit interface for prescription input, real-time gate visualization, and audit inspection).
- **Acceptance Criteria:**
  - Provides quick test slip templates (Routine Amoxicillin, High-Cost Adalimumab, Fraudulent NMC).
  - Displays tri-state badges (`READY TO DISPENSE`, `CMO REVIEW NEEDED`, `REJECTED`).
