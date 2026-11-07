"""FastAPI REST Service Wrapper for MedClaim Rx Copilot.

Exposes OpenAPI / Swagger-documented endpoints for:
  - GET /health: Health checks on SQLite strong-room and ChromaDB vector collection.
  - POST /triage: LangGraph 3-station prior-authorization pipeline execution.
  - POST /action-gate: 3-tier action gate permissions evaluator.
"""

import sys
from pathlib import Path

# Ensure root dir is present on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from app.graph import graph, COST_GATE, CONF_GATE
from app.packet import create_claim_packet
from app.router import evaluate_action_gate, classify_request
from app.tools import get_db_connection, DEFAULT_DB_PATH
from app.memory import get_chroma_client, DEFAULT_COLLECTION_NAME

app = FastAPI(
    title="MedClaim Rx Copilot API",
    version="0.2.0",
    description="Deterministic Prior-Authorization, Clinical RAG, and 3-Tier Clinical Governance Desk API",
)


class TriageRequest(BaseModel):
    raw_text: str = Field(
        ...,
        description="Prescription slip text or clinical triage note.",
        example=(
            "Prescriber: Dr. Sharma\n"
            "License: NMC-2019-4410\n"
            "Drug: RX-AMOX-500\n"
            "Diagnosis: Bacterial Sinusitis\n"
            "Cost: INR 1,450.00"
        ),
    )
    claim_id: Optional[str] = Field(None, description="Optional custom claim identifier.")


class ActionGateRequest(BaseModel):
    command: str = Field(
        ...,
        description="Action command or clinical inquiry.",
        example="Approve routine antibiotic Amoxicillin for ₹1,450",
    )
    role: str = Field("operator", description="User role: 'operator' or 'cmo_approver'.")
    cost_inr: float = Field(0.0, description="Cost of the associated claim in INR.")


@app.get("/health", tags=["Monitoring"])
def health_check() -> Dict[str, Any]:
    """Inspect operational health of SQLite strong-room and ChromaDB RAG store."""
    sqlite_ok = False
    doc_count = 0
    drug_count = 0
    claim_count = 0

    try:
        conn = get_db_connection(DEFAULT_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM prescribers;")
        doc_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM formulary;")
        drug_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM claims;")
        claim_count = cursor.fetchone()[0]
        conn.close()
        sqlite_ok = True
    except Exception as e:
        sqlite_ok = False

    chroma_count = 0
    chroma_ok = False
    try:
        client = get_chroma_client()
        if hasattr(client, "get_or_create_collection"):
            coll = client.get_or_create_collection(DEFAULT_COLLECTION_NAME)
            chroma_count = coll.count()
        elif hasattr(client, "count"):
            chroma_count = client.count(DEFAULT_COLLECTION_NAME)
        chroma_ok = True
    except Exception:
        chroma_ok = False

    is_healthy = sqlite_ok and chroma_ok

    return {
        "status": "healthy" if is_healthy else "degraded",
        "service": "MedClaim Rx Copilot API",
        "version": "0.2.0",
        "sqlite_strong_room": {
            "connected": sqlite_ok,
            "verified_prescribers": doc_count,
            "formulary_drugs": drug_count,
            "recorded_claims": claim_count,
        },
        "chromadb_rag": {
            "connected": chroma_ok,
            "policy_chunks": chroma_count,
            "collection": DEFAULT_COLLECTION_NAME,
        },
        "gates": {
            "cost_gate_inr": COST_GATE,
            "conf_gate_min": CONF_GATE,
        },
    }


@app.post("/triage", tags=["Clinical Triage"])
def triage_prescription(req: TriageRequest) -> Dict[str, Any]:
    """Execute the deterministic 3-station LangGraph triage workflow on a prescription slip.

    Guards explicitly against silent failure and empty payloads.
    """
    clean_text = (req.raw_text or "").strip()
    if not clean_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Silent-Failure Guard: raw_text must not be empty or whitespace.",
        )

    # Construct initial ClaimPacket state
    packet = create_claim_packet(
        raw_text=clean_text,
        claim_id=req.claim_id,
    )

    try:
        result = graph.invoke(packet)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LangGraph execution exception: {str(err)}",
        )

    if not result or not isinstance(result, dict) or "status" not in result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Triage engine returned an uninitialized or empty state contract.",
        )

    return result


@app.post("/action-gate", tags=["Clinical Governance"])
def check_action_gate(req: ActionGateRequest) -> Dict[str, Any]:
    """Validate user command against the 3-Tier Action Permission Gate.

    Distinguishes advisory inquiries from imperative commands and enforces
    Operator vs. CMO Approver role restrictions.
    """
    clean_cmd = (req.command or "").strip()
    if not clean_cmd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing command: command cannot be empty.",
        )

    evaluation = evaluate_action_gate(
        command=clean_cmd,
        role=req.role,
        cost_inr=req.cost_inr,
    )
    return evaluation
