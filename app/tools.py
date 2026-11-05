"""SQLite Strong-Room and Verification Tools for MedClaim Rx.

Manages ACID-compliant local database tables for NMC doctor licenses,
hospital formulary records, and claims audit logs.
"""

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = "data/medclaim.db"


def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Create a SQLite connection pointing to db_path with Row factory enabled."""
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    return conn


def init_db_schema(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize table schemas for prescribers, formulary, and claims."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS prescribers (
            license_no TEXT PRIMARY KEY,
            doctor_name TEXT NOT NULL,
            specialty TEXT,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS formulary (
            drug_code TEXT PRIMARY KEY,
            drug_name TEXT NOT NULL,
            category TEXT,
            tier INTEGER NOT NULL DEFAULT 1,
            is_formulary INTEGER NOT NULL DEFAULT 1,
            requires_cmo INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS claims (
            claim_id TEXT PRIMARY KEY,
            prescriber TEXT,
            license_no TEXT,
            drug_code TEXT,
            diagnosis TEXT,
            cost_inr REAL,
            confidence REAL,
            status TEXT NOT NULL,
            gate TEXT NOT NULL,
            policy_hits TEXT,
            trace TEXT,
            prompt_version TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    conn.commit()
    conn.close()
