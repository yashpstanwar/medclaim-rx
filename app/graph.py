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
