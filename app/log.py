"""PII-Safe Observability, Token Cost Receipt, and JSONL Trace Logger for MedClaim Rx.

Appends sanitized operational execution traces to logs/medclaim.jsonl.
Ensures zero patient names, Aadhaar identifiers, or raw clinical prose
are committed to persistent audit logs.

Provides latency_ms tracking and comparative token cost receipt estimation:
  - Zero-Cost Deterministic Path: $0.00
  - Groq Cloud API: ~$0.06–$1.24/mo at scale
  - Local Llama.cpp: $0.00 API inference
"""

from pathlib import Path
from datetime import datetime, timezone
import json
from typing import Optional, Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT_DIR / "logs"
LOG_PATH = LOG_DIR / "medclaim.jsonl"

# Ensure logs directory exists on module load
LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_utc_timestamp() -> str:
    """Generate ISO-8601 formatted UTC timestamp with timezone offset."""
    return datetime.now(timezone.utc).isoformat()


def estimate_token_cost(raw_text: str = "", policy_hits: Any = "") -> Dict[str, Any]:
    """Calculate token count heuristic and compare operational costs across backends.

    Compares:
      1. Zero-Cost Deterministic Path: $0.00 (Rules + Local SQLite + ChromaDB)
      2. Groq Cloud API Projected Cost: ~$0.06–$1.24/month at production scale
      3. Local Llama.cpp: $0.00 API inference cost (Self-hosted open weights)

    Args:
        raw_text: Prescription note text.
        policy_hits: Retrieved RAG policy statements.

    Returns:
        Structured token and cost receipt dictionary.
    """
    text_content = str(raw_text or "")
    hits_content = str(policy_hits or "")
    combined = text_content + " " + hits_content

    # Standard heuristic: ~4 characters per token
    prompt_tokens = max(15, len(combined) // 4)
    completion_tokens = 45  # Standard structured triage ClaimPacket verdict
    total_tokens = prompt_tokens + completion_tokens

    # Groq Llama-3-70b scale: ~$0.05 / 1M prompt, ~$0.08 / 1M completion
    groq_per_query = (prompt_tokens * 0.05 / 1_000_000.0) + (completion_tokens * 0.08 / 1_000_000.0)

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "deterministic_cost_usd": 0.0,
        "groq_cost_usd": round(groq_per_query, 8),
        "groq_monthly_projected_usd": "0.06 - 1.24",
        "local_llamacpp_cost_usd": 0.0,
        "cost_summary": "Zero-Cost Deterministic: $0.00 | Groq Cloud: ~$0.06–$1.24/mo | Local Llama.cpp: $0.00",
    }


def write_trace(packet: Dict[str, Any], log_path: Path = LOG_PATH) -> None:
    """Append a single sanitized JSON line with operational metadata to log_path.

    Records strictly operational fields:
      - ts: Current UTC ISO-8601 timestamp
      - claim_id: Unique claim identifier
      - prompt_version: Extraction parser version
      - status: Final workflow status
      - gate: Triggered gate name
      - trace: Chronological node execution path
      - cost_inr: Calculated prescription cost
      - latency_ms: Execution duration in milliseconds
      - estimated_tokens: Estimated prompt + completion tokens

    Guarantees:
      - Never writes raw_text, patient names, diagnoses, or sensitive PII to disk.
    """
    latency = float(packet.get("latency_ms", 0.0))
    token_est = packet.get("estimated_tokens")
    if token_est is None:
        receipt = estimate_token_cost(packet.get("raw_text", ""), packet.get("policy_hits", ""))
        token_est = receipt["total_tokens"]

    trace_entry = {
        "ts": get_utc_timestamp(),
        "claim_id": packet.get("claim_id", ""),
        "prompt_version": packet.get("prompt_version", ""),
        "status": packet.get("status", ""),
        "gate": packet.get("gate", ""),
        "trace": packet.get("trace", []),
        "cost_inr": float(packet.get("cost_inr", 0.0)),
        "latency_ms": round(latency, 3),
        "estimated_tokens": int(token_est),
    }

    log_file = Path(log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(trace_entry) + "\n")
