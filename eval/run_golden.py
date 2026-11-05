"""MedClaim Rx Golden Set Evaluation and Regression Benchmark Suite.

Executes frozen test cases against the LangGraph prior-authorization pipeline
to ensure deterministic gating, prompt injection resistance, and zero false approvals.
"""

from typing import Dict, Any, List
from app.graph import graph
from app.packet import create_claim_packet

CASES: List[Dict[str, Any]] = [
    {
        "id": "G01_CLEAN",
        "description": "Routine Generic Antibiotic (Dr. Sharma, Amoxicillin, ₹1,450)",
        "raw": (
            "Prescriber: Dr. Sharma\n"
            "License: NMC-2019-4410\n"
            "Drug: RX-AMOX-500\n"
            "Diagnosis: Bacterial Pharyngitis\n"
            "Cost: ₹1,450.00"
        ),
        "expected_status": "ready_to_dispense",
        "expected_gate": "none",
    },
    {
        "id": "G02_HIGH_BIOLOGIC",
        "description": "High-Cost Biologic Gate (Dr. Verma, Adalimumab, ₹68,000 >= ₹25k)",
        "raw": (
            "Doctor: Dr. Verma\n"
            "License: NMC-2016-8821\n"
            "Drug: RX-ADAL-40\n"
            "Diagnosis: Severe Rheumatoid Arthritis\n"
            "Cost: ₹68,000.00"
        ),
        "expected_status": "needs_pharmacist_review",
        "expected_gate": "high_cost_gate",
    },
]
