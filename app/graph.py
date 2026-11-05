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
    current_trace = list(state.get("trace") or [])
    updated_trace = current_trace + ["extract"]
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
