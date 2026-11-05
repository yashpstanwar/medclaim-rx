# Issue #01: Strongly-Typed ClaimPacket State Contract

**Label:** `architecture` `state-management` `type-safety`  
**Milestone:** Day 1 Foundation  
**Assignee:** Core Backend Agent  

---

## 📌 Context
In safety-critical clinical applications, pipeline state passing between nodes must be deterministic, strictly typed, and transparent. We need a `ClaimPacket` state contract that models both raw intake, extracted clinical parameters, policy RAG hits, and an audit trail.

## 🎯 Requirements
1. Define `ClaimPacket` using `typing.TypedDict` (or Python 3.12 syntax).
2. Field structure:
   - **Identity Fields:**
     - `claim_id: str` (Unique UUID/Hash string)
     - `raw_text: str` (Original unedited Rx text/slip)
     - `prescriber: str` (Doctor name)
     - `license_no: str` (NMC registration code)
   - **Clinical Fields:**
     - `drug_code: str` (Hospital formulary code, e.g. RX-AMOX-500)
     - `diagnosis: str` (Indication/ICD note)
     - `cost_inr: float` (Cost in Indian Rupees)
     - `confidence: float` (Extraction confidence between 0.0 and 1.0)
   - **Observability & Routing Attributes:**
     - `status: str` (Workflow status: `pending`, `ready_to_dispense`, `cmo_review_needed`, `pharmacist_review_needed`, `rejected_invalid`)
     - `gate: str` (Active gate identifier)
     - `policy_hits: list[str]` (Semantic chunks retrieved from ChromaDB)
     - `trace: list[str]` (Execution breadcrumbs of graph nodes visited)
     - `prompt_version: str` (Prompt/parser version tag)

## ✅ Acceptance Criteria
- Unit tests verify instantiation with valid fields.
- Factory helper or empty packet creator initializes safe defaults without null pointer risks.
