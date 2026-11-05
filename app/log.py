"""PII-Safe Observability and JSONL Trace Logger for MedClaim Rx.

Appends sanitized operational execution traces to logs/medclaim.jsonl.
Ensures zero patient names, Aadhaar identifiers, or raw clinical prose
are committed to persistent audit logs.
"""

from pathlib import Path
from datetime import datetime, timezone
import json
from typing import Optional, Dict, Any

LOG_DIR = Path("logs")
LOG_PATH = LOG_DIR / "medclaim.jsonl"

# Ensure logs directory exists on module load
LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_utc_timestamp() -> str:
    """Generate ISO-8601 formatted UTC timestamp with timezone offset."""
    return datetime.now(timezone.utc).isoformat()


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

    Guarantees:
      - Never writes raw_text, patient names, diagnoses, or sensitive PII to disk.
    """
    trace_entry = {
        "ts": get_utc_timestamp(),
        "claim_id": packet.get("claim_id", ""),
        "prompt_version": packet.get("prompt_version", ""),
        "status": packet.get("status", ""),
        "gate": packet.get("gate", ""),
        "trace": packet.get("trace", []),
        "cost_inr": float(packet.get("cost_inr", 0.0)),
    }

    log_file = Path(log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(trace_entry) + "\n")
