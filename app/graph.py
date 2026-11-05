"""MedClaim Rx LangGraph 3-Station Core Workflow Engine.

Orchestrates deterministic prescription claim intake across 3 stations:
  1. extract_node (Deterministic labelled slip parsing)
  2. policy_node (SQLite registers, Chroma RAG guidelines & clinical gates)
  3. route_node (Final disposition, SQLite audit ledger & PII-safe JSONL log)
"""

from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END

from app.packet import ClaimPacket, create_claim_packet
from app.extract_lab import parse_labelled
from app.tools import check_license, lookup_formulary, retrieve_policy, save_claim, seed_db
from app.memory import seed_policy
from app.log import write_trace

# Deterministic Clinical Gating Constants
COST_GATE: float = 25000.0
CONF_GATE: float = 0.80


def extract_node(state: ClaimPacket) -> Dict[str, Any]:
    """Station 1: Extract clinical parameters from raw prescription slip text."""
    parsed = parse_labelled(state.get("raw_text", ""))
    existing_trace = [t for t in (state.get("trace") or []) if t != "INTAKE"]
    updated_trace = existing_trace + ["extract"] if "extract" not in existing_trace else existing_trace
    return {
        "prescriber": parsed.get("prescriber", ""),
        "license_no": parsed.get("license_no", ""),
        "drug_code": parsed.get("drug_code", ""),
        "diagnosis": parsed.get("diagnosis", ""),
        "cost_inr": parsed.get("cost_inr", 0.0),
        "confidence": parsed.get("confidence", 0.0),
        "prompt_version": parsed.get("prompt_version", "lab_labels_v1"),
        "status": "extracted",
        "trace": updated_trace,
    }


def policy_node(state: ClaimPacket) -> Dict[str, Any]:
    """Station 2: Clinical Policy, Licensure, and Formulary Verification."""
    current_trace = list(state.get("trace") or [])
    policy_trace = current_trace + ["policy"]

    # Gate 1: Extraction confidence check
    if state.get("confidence", 0.0) < CONF_GATE:
        return {
            "status": "needs_pharmacist_review",
            "gate": "needs_typecheck",
            "trace": policy_trace,
        }

    # Gate 2: ChromaDB RAG policy retrieval & fail-closed empty shelf check
    hits = retrieve_policy("NMC license verification formulary and high cost biologic stamp rules")
    if not hits:
        return {
            "status": "needs_pharmacist_review",
            "gate": "empty_policy",
            "policy_hits": "",
            "trace": policy_trace,
        }

    # Gate 3: Prescriber NMC license verification
    license_result = check_license(state.get("license_no", ""))
    if str(license_result).startswith("UNKNOWN"):
        return {
            "status": "needs_pharmacist_review",
            "gate": "license_mismatch",
            "policy_hits": hits,
            "trace": policy_trace,
        }

    # Gate 4: Hospital formulary verification
    formulary_result = lookup_formulary(state.get("drug_code", ""))
    if str(formulary_result).startswith("MISSING"):
        return {
            "status": "needs_pharmacist_review",
            "gate": "non_formulary",
            "policy_hits": hits,
            "trace": policy_trace,
        }

    # Gate 5: High-cost biologic / specialty cost gate
    if float(state.get("cost_inr", 0.0)) >= COST_GATE:
        return {
            "status": "needs_pharmacist_review",
            "gate": "high_cost_gate",
            "policy_hits": hits,
            "trace": policy_trace,
        }

    # All gates passed: ready for final routing
    return {
        "status": "ok_for_route",
        "gate": "none",
        "policy_hits": hits,
        "trace": policy_trace,
    }


def route_node(state: ClaimPacket) -> Dict[str, Any]:
    """Station 3: Final disposition, SQLite persistence & PII-safe JSONL audit logging."""
    current_status = state.get("status", "pending")
    final_status = (
        "needs_pharmacist_review"
        if current_status == "needs_pharmacist_review"
        else "ready_to_dispense"
    )

    current_trace = list(state.get("trace") or [])
    final_trace = current_trace + ["route"]

    # Construct complete packet for persistence
    final_packet = dict(state)
    final_packet["status"] = final_status
    final_packet["trace"] = final_trace

    # Persist to SQLite strong-room and write PII-safe JSONL trace
    save_claim(final_packet)  # type: ignore
    write_trace(final_packet)

    return {
        "status": final_status,
        "trace": final_trace,
    }


def create_medclaim_graph():
    """Build and compile the 3-station LangGraph workflow."""
    builder = StateGraph(ClaimPacket)

    # Register the 3 stations
    builder.add_node("extract", extract_node)
    builder.add_node("policy", policy_node)
    builder.add_node("route", route_node)

    # Linear deterministic pipeline edges: START -> extract -> policy -> route -> END
    builder.add_edge(START, "extract")
    builder.add_edge("extract", "policy")
    builder.add_edge("policy", "route")
    builder.add_edge("route", END)

    return builder.compile()


# Auto-seed SQLite strong-room and ChromaDB policy handbook on module initialization
try:
    seed_db()
    seed_policy()
except Exception:
    pass

# Compiled LangGraph workflow instance
graph = create_medclaim_graph()
