# Issue #05: LangGraph Deterministic State Machine & Clinical Routing

**Label:** `langgraph` `workflow` `clinical-safety`  
**Milestone:** Day 1-2 Progression  
**Assignee:** Core Backend Agent  

---

## 📌 Context
MedClaim Rx executes via a deterministic LangGraph state machine. Claims travel through functional nodes (`extract_node` -> `policy_node` -> `route_node`) where state transitions enforce hospital policy and fail-closed safety constraints.

## 🎯 Requirements
1. Graph State:
   - Typed `ClaimPacket` passed along graph channels.
2. Nodes:
   - `extract_node`: Runs labelled parser or LLM fallback; populates clinical fields and confidence.
   - `policy_node`: Invokes SQLite `check_license`, `lookup_formulary`, and Chroma RAG; appends policy hits to state.
   - `route_node`: Enforces deterministic gating rules (`COST_GATE`, `CONF_GATE`) and transitions `status`.
3. Routing Outcomes:
   - `ready_to_dispense`: Valid license, on formulary, cost < ₹25,000, confidence >= 0.80.
   - `cmo_review_needed`: Valid license, on formulary, cost >= ₹25,000.
   - `pharmacist_review_needed`: Off-formulary drug, or confidence < 0.80.
   - `rejected_invalid`: Unverified/missing license.

## ✅ Acceptance Criteria
- End-to-end execution of graph produces traceable state transitions.
- Graph guarantees fail-closed termination when database checks fail.
