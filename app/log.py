"""PII-Safe Observability and JSONL Trace Logger for MedClaim Rx.

Appends sanitized operational execution traces to logs/medclaim.jsonl.
Ensures zero patient names, Aadhaar identifiers, or raw clinical prose
are committed to persistent audit logs.
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

LOG_DIR = Path("logs")
LOG_PATH = LOG_DIR / "medclaim.jsonl"

# Ensure logs directory exists on module load
LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_utc_timestamp() -> str:
    """Generate ISO-8601 formatted UTC timestamp with timezone offset."""
    return datetime.now(timezone.utc).isoformat()
