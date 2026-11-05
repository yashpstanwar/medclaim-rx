"""Deterministic Labelled Prescription Slip Extractor for MedClaim Rx.

Parses structured key-value prescription slips without LLM inference,
sanitizes currency notations, converts amounts to floats, and assigns
deterministic confidence scores based on field completeness.
"""

import re
from typing import Dict, Any, Optional
from app.packet import ClaimPacket, create_claim_packet

PROMPT_VERSION = "lab_labels_v1"

# Regex patterns for key detection in multi-line slips
PATTERNS = {
    "prescriber": [
        r"^(?:prescriber|doctor|physician|dr\.?)\s*[:=-]\s*(.+)$",
    ],
    "license_no": [
        r"^(?:license(?:\s*no\.?)?|nmc(?:\s*no\.?)?|reg(?:\s*no\.?)?|registration)\s*[:=-]\s*(.+)$",
    ],
    "drug_code": [
        r"^(?:drug(?:\s*code)?|medication|rx|medicine|item)\s*[:=-]\s*(.+)$",
    ],
    "diagnosis": [
        r"^(?:diagnosis|indication|condition|clinical\s*indication)\s*[:=-]\s*(.+)$",
    ],
    "cost": [
        r"^(?:cost(?:\s*inr)?|amount|price|total(?:\s*cost)?)\s*[:=-]\s*(.+)$",
    ],
}


def sanitize_currency(val: str) -> Optional[float]:
    """Sanitize currency string removing symbols (₹, INR, Rs., commas) and convert to float.

    Examples:
        '₹30,000' -> 30000.0
        'Rs. 1,500.50/-' -> 1500.5
        'INR 25,000' -> 25000.0
        'invalid' -> None
    """
    if not val:
        return None

    cleaned = val.strip()
    # Remove currency abbreviations and symbols
    cleaned = re.sub(r"(?i)(?:inr|rs\.?|rupees|₹|/-)", "", cleaned)
    # Remove commas and excessive whitespace
    cleaned = cleaned.replace(",", "").strip()

    # Extract first numeric float match
    match = re.search(r"[-+]?\d*\.?\d+", cleaned)
    if match:
        try:
            return round(float(match.group()), 2)
        except ValueError:
            return None
    return None


def parse_labelled(raw: str) -> Dict[str, Any]:
    """Parse structured key-value prescription slip text.

    Scans line-by-line for known prescription keys, cleans extracted values,
    converts cost to float, and scores extraction confidence.

    Rules:
      - Valid cost parsed: confidence = 0.95
      - Missing or invalid cost: confidence = 0.40

    Args:
        raw: Raw multi-line prescription slip string.

    Returns:
        Dictionary containing extracted clinical parameters and confidence score.
    """
    if not raw or not raw.strip():
        return {
            "prescriber": "",
            "license_no": "",
            "drug_code": "",
            "diagnosis": "",
            "cost_inr": 0.0,
            "confidence": 0.0,
            "prompt_version": PROMPT_VERSION,
            "raw_text": raw or "",
        }

    extracted: Dict[str, str] = {
        "prescriber": "",
        "license_no": "",
        "drug_code": "",
        "diagnosis": "",
        "cost": "",
    }

    lines = raw.strip().splitlines()
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        for field, patterns in PATTERNS.items():
            if extracted[field]:
                continue  # already found
            for pat in patterns:
                m = re.match(pat, line_clean, re.IGNORECASE)
                if m:
                    extracted[field] = m.group(1).strip()
                    break

    # Sanitize cost
    cost_float = sanitize_currency(extracted["cost"])

    # Score confidence
    if cost_float is not None and cost_float > 0.0:
        confidence = 0.95
        cost_inr = cost_float
    elif cost_float is not None and cost_float == 0.0:
        confidence = 0.40
        cost_inr = 0.0
    else:
        # Missing or unparseable cost
        confidence = 0.40
        cost_inr = 0.0

    return {
        "prescriber": extracted["prescriber"],
        "license_no": extracted["license_no"],
        "drug_code": extracted["drug_code"],
        "diagnosis": extracted["diagnosis"],
        "cost_inr": cost_inr,
        "confidence": confidence,
        "prompt_version": PROMPT_VERSION,
        "raw_text": raw,
    }


def parse_to_packet(raw: str, claim_id: Optional[str] = None) -> ClaimPacket:
    """Convenience helper to parse raw text directly into a ClaimPacket."""
    parsed = parse_labelled(raw)
    return create_claim_packet(
        claim_id=claim_id,
        raw_text=raw,
        prescriber=parsed["prescriber"],
        license_no=parsed["license_no"],
        drug_code=parsed["drug_code"],
        diagnosis=parsed["diagnosis"],
        cost_inr=parsed["cost_inr"],
        confidence=parsed["confidence"],
        prompt_version=parsed["prompt_version"],
        trace=["INTAKE", "EXTRACT_LABELLED"],
    )
