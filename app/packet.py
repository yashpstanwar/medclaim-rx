"""ClaimPacket State Contract for MedClaim Rx.

Defines the strongly-typed TypedDict that flows through the LangGraph state machine.
"""

from typing import TypedDict, List, Optional
import uuid


class ClaimPacket(TypedDict):
    """Strongly-typed claim packet state contract.

    Attributes:
        claim_id: Unique identifier for the claim packet.
        raw_text: Original raw input text of the prescription slip or clinical note.
        prescriber: Name of the prescribing doctor (e.g. 'Dr. Sharma').
        license_no: National Medical Commission (NMC) registration license number.
        drug_code: Hospital formulary drug code (e.g. 'RX-AMOX-500').
        diagnosis: Clinical diagnosis or clinical indication note.
        cost_inr: Total calculated prescription cost in Indian Rupees (INR).
        confidence: Extraction confidence score (0.0 to 1.0).
        status: Workflow lifecycle status:
            - 'pending': Intake in progress.
            - 'ready_to_dispense': Recommended for pharmacist clearance.
            - 'cmo_review_needed': Requires Chief Medical Officer authorization.
            - 'pharmacist_review_needed': Requires therapeutic substitution or clerk review.
            - 'rejected_invalid': Unverified license or fraudulent claim.
        gate: Identifier of the decisive gate or rule triggered.
        policy_hits: List of semantic clinical policy snippets retrieved from ChromaDB.
        trace: Chronological audit trail of visited pipeline nodes and decisions.
        prompt_version: Identifier of the prompt or parser version used.
    """

    # Identity Fields
    claim_id: str
    raw_text: str
    prescriber: str
    license_no: str

    # Clinical Fields
    drug_code: str
    diagnosis: str
    cost_inr: float
    confidence: float

    # Observability & Routing Attributes
    status: str
    gate: str
    policy_hits: List[str]
    trace: List[str]
    prompt_version: str


def create_claim_packet(
    raw_text: str = "",
    prescriber: str = "",
    license_no: str = "",
    drug_code: str = "",
    diagnosis: str = "",
    cost_inr: float = 0.0,
    confidence: float = 0.0,
    status: str = "pending",
    gate: str = "INTAKE",
    policy_hits: Optional[List[str]] = None,
    trace: Optional[List[str]] = None,
    prompt_version: str = "v1.0",
    claim_id: Optional[str] = None,
) -> ClaimPacket:
    """Factory helper to construct a properly typed ClaimPacket with defaults."""
    return ClaimPacket(
        claim_id=claim_id or f"CLM-{uuid.uuid4().hex[:8].upper()}",
        raw_text=raw_text,
        prescriber=prescriber,
        license_no=license_no,
        drug_code=drug_code,
        diagnosis=diagnosis,
        cost_inr=float(cost_inr),
        confidence=float(confidence),
        status=status,
        gate=gate,
        policy_hits=list(policy_hits) if policy_hits is not None else [],
        trace=list(trace) if trace is not None else ["INTAKE"],
        prompt_version=prompt_version,
    )
