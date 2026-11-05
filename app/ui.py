"""MedClaim Rx — Clinical Prior-Authorization & Formulary Desk.

Interactive Streamlit Console featuring:
  - Tab 1: Live Prescription Triage Desk
  - Tab 2: Golden Set Benchmark Exam (G01–G05)
  - Tab 3: Observability Diary & Strong-Room Ledger
"""

import streamlit as st
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List

# Page Configuration
st.set_page_config(
    page_title="MedClaim Rx — Clinical Desk",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Obsidian High-Contrast Dark-Mode Theme CSS
DARK_THEME_CSS = """
<style>
    /* Obsidian Base Styling */
    .stApp {
        background-color: #0B0C10;
        color: #C5C6C7;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Headers & Text */
    h1, h2, h3, h4, h5, h6 {
        color: #66FCF1 !important;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    /* Electric Cyan Badges & Pass Indicators */
    .badge-pass {
        background: linear-gradient(135deg, rgba(0, 240, 255, 0.15), rgba(102, 252, 241, 0.25));
        border: 1px solid #00F0FF;
        color: #00F0FF !important;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
        display: inline-block;
        box-shadow: 0 0 10px rgba(0, 240, 255, 0.2);
    }
    
    /* Champagne Gold Review Badges */
    .badge-review {
        background: linear-gradient(135deg, rgba(212, 175, 55, 0.15), rgba(255, 215, 0, 0.25));
        border: 1px solid #D4AF37;
        color: #D4AF37 !important;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
        display: inline-block;
        box-shadow: 0 0 10px rgba(212, 175, 55, 0.2);
    }
    
    /* Station Pills */
    .station-pill {
        background-color: #1F2833;
        border: 1px solid #45A29E;
        color: #66FCF1;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-right: 6px;
        display: inline-block;
    }
    
    /* Metric Cards */
    div[data-testid="stMetricValue"] {
        color: #66FCF1 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #C5C6C7 !important;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #12141A;
        border-right: 1px solid #1F2833;
    }
    
    /* Inputs & Textareas */
    .stTextArea textarea {
        background-color: #12141A !important;
        color: #E0E0E0 !important;
        border: 1px solid #1F2833 !important;
        border-radius: 8px;
    }
    .stTextInput input {
        background-color: #12141A !important;
        color: #E0E0E0 !important;
        border: 1px solid #1F2833 !important;
        border-radius: 8px;
    }
</style>
"""
st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)


def fetch_table_rows(query: str, db_path: str = "data/medclaim.db") -> List[Dict[str, Any]]:
    """Execute read-only SQL query against SQLite strong-room."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


def read_jsonl_traces(log_path: str = "logs/medclaim.jsonl", limit: int = 50) -> List[Dict[str, Any]]:
    """Read latest operational trace records from PII-safe JSONL log."""
    path = Path(log_path)
    if not path.exists():
        return []
    records = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line_clean = line.strip()
                if line_clean:
                    try:
                        records.append(json.loads(line_clean))
                    except Exception:
                        pass
        return list(reversed(records))[:limit]
    except Exception:
        return []

from app.graph import graph, COST_GATE, CONF_GATE
from app.tools import seed_db
from app.memory import seed_policy, get_chroma_client, DEFAULT_COLLECTION_NAME

# Sidebar: Governance & Strong-Room Status
with st.sidebar:
    st.title("⚙️ Clinical Governance")
    st.markdown("### Deterministic Python Gates")
    st.metric("COST_GATE (INR)", f"₹{COST_GATE:,.2f}")
    st.metric("CONF_GATE (Min Score)", f"{CONF_GATE:.2f}")

    st.markdown("---")
    st.markdown("### Strong-Room Status")

    # Live Database Counts
    doc_count = len(fetch_table_rows("SELECT license_no FROM prescribers"))
    drug_count = len(fetch_table_rows("SELECT drug_code FROM formulary"))
    claim_count = len(fetch_table_rows("SELECT claim_id FROM claims"))

    try:
        client = get_chroma_client()
        if hasattr(client, "get_or_create_collection"):
            coll = client.get_or_create_collection(DEFAULT_COLLECTION_NAME)
            chroma_count = coll.count()
        elif hasattr(client, "count"):
            chroma_count = client.count(DEFAULT_COLLECTION_NAME)
        else:
            chroma_count = 0
    except Exception:
        chroma_count = 0

    st.write(f"🩺 **Verified Doctors:** `{doc_count}`")
    st.write(f"💊 **Formulary Drugs:** `{drug_count}`")
    st.write(f"📜 **Chroma Policy Chunks:** `{chroma_count}`")
    st.write(f"📁 **Adjudicated Claims:** `{claim_count}`")

    st.markdown("---")
    if st.button("🔄 Re-Seed Strong-Room (DB + RAG)", use_container_width=True):
        seed_db()
        chunks_seeded = seed_policy()
        st.success(f"Strong-room re-seeded ({chunks_seeded} policy chunks).")
        st.rerun()
