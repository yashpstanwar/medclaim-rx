"""SQLite Strong-Room and Verification Tools for MedClaim Rx.

Manages ACID-compliant local database tables for NMC doctor licenses,
hospital formulary records, and claims audit logs.
Provides parameterized SQL lookup tools and persistence helpers.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

from app.packet import ClaimPacket
from app.memory import retrieve_policy_chunks, DEFAULT_CHROMA_DIR, DEFAULT_COLLECTION_NAME

DEFAULT_DB_PATH = "data/medclaim.db"


def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Create a SQLite connection pointing to db_path with Row factory enabled."""
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    return conn


def seed_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize schema and seed authoritative registry data.

    Provisions:
      - prescribers: Authoritative NMC registrations.
      - formulary: Approved hospital drugs and pricing tiers.
      - claims: Immutable audit ledger.

    Verified Prescribers:
      - Dr. Sharma (NMC-2019-4410)
      - Dr. Verma (NMC-2016-8821)
      Note: NMC-99INVALID is intentionally unseeded.

    Formulary Drugs:
      - RX-AMOX-500 (Amoxicillin 500mg)
      - RX-ADAL-40 (Adalimumab 40mg)
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # DDL: Create Tables
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

    # Seed Verified Prescribers
    prescribers_data = [
        ("NMC-2019-4410", "Dr. Sharma", "General Medicine", "ACTIVE"),
        ("NMC-2016-8821", "Dr. Verma", "Rheumatology & Immunology", "ACTIVE"),
    ]
    cursor.executemany(
        """
        INSERT OR REPLACE INTO prescribers (license_no, doctor_name, specialty, status)
        VALUES (?, ?, ?, ?);
        """,
        prescribers_data,
    )

    # Seed Formulary Drugs
    formulary_data = [
        (
            "RX-AMOX-500",
            "Amoxicillin 500mg Oral Capsule",
            "Antibiotic / General",
            1,
            1,
            0,
        ),
        (
            "RX-ADAL-40",
            "Adalimumab 40mg Prefilled Syringe",
            "Biologic / Monoclonal Antibody",
            3,
            1,
            1,
        ),
    ]
    cursor.executemany(
        """
        INSERT OR REPLACE INTO formulary (drug_code, drug_name, category, tier, is_formulary, requires_cmo)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        formulary_data,
    )

    conn.commit()
    conn.close()


def check_license(
    license_no: str, db_path: str = DEFAULT_DB_PATH
) -> Optional[Dict[str, Any]]:
    """Query authoritative prescriber registry using bound SQL parameter.

    Args:
        license_no: NMC registration number (e.g. 'NMC-2019-4410').
        db_path: Path to medclaim.db.

    Returns:
        Prescriber record as a dictionary if found, else None.
    """
    if not license_no or not license_no.strip():
        return None

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT license_no, doctor_name, specialty, status FROM prescribers WHERE license_no = ?",
        (license_no.strip(),),
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def lookup_formulary(
    drug_code: str, db_path: str = DEFAULT_DB_PATH
) -> Optional[Dict[str, Any]]:
    """Query hospital formulary master using bound SQL parameter.

    Args:
        drug_code: Drug formulary identifier (e.g. 'RX-AMOX-500').
        db_path: Path to medclaim.db.

    Returns:
        Formulary item record as a dictionary if found, else None.
    """
    if not drug_code or not drug_code.strip():
        return None

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT drug_code, drug_name, category, tier, is_formulary, requires_cmo
        FROM formulary
        WHERE drug_code = ?
        """,
        (drug_code.strip(),),
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def retrieve_policy(
    query: str,
    n_results: int = 3,
    persist_dir: str = DEFAULT_CHROMA_DIR,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> List[str]:
    """Retrieve top relevant clinical policy statements from Chroma RAG handbook."""
    return retrieve_policy_chunks(
        query=query,
        n_results=n_results,
        persist_dir=persist_dir,
        collection_name=collection_name,
    )


def save_claim(packet: ClaimPacket, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Persist a completed ClaimPacket into the SQLite claims audit ledger.

    Args:
        packet: Strongly-typed ClaimPacket instance.
        db_path: Path to medclaim.db.

    Returns:
        True if persisted successfully, False otherwise.
    """
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO claims (
                claim_id, prescriber, license_no, drug_code, diagnosis,
                cost_inr, confidence, status, gate, policy_hits, trace, prompt_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                packet["claim_id"],
                packet.get("prescriber", ""),
                packet.get("license_no", ""),
                packet.get("drug_code", ""),
                packet.get("diagnosis", ""),
                float(packet.get("cost_inr", 0.0)),
                float(packet.get("confidence", 0.0)),
                packet.get("status", "pending"),
                packet.get("gate", "INTAKE"),
                json.dumps(packet.get("policy_hits", [])),
                json.dumps(packet.get("trace", [])),
                packet.get("prompt_version", "v1.0"),
            ),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False
