# app/ui.py — Minimalist Clinical Workbench (ApexResolve / Linear Design System)
import sys
from pathlib import Path

# Ensure repository root is on sys.path for Streamlit Cloud deployment
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
import uuid
import streamlit as st

from app.graph import graph, COST_GATE, CONF_GATE
from app.tools import connect, seed_db
from app.memory import seed_policy, policy_collection
from app.router import classify_request, evaluate_action_gate
from eval.run_golden import CASES

st.set_page_config(
    page_title="MedClaim Rx — Clinical Prior-Authorization",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Minimalist Design System (Zero Emojis, Hairline Borders, Inter + Mono)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Hide native Streamlit chrome that makes apps look like prototypes */
    #MainMenu, footer, header, [data-testid="stToolbar"], [data-testid="stDecoration"] {
        display: none !important;
    }
    [data-testid="stSidebar"], [data-testid="collapsedControl"] {
        display: none !important;
    }

    html, body, [class*="css"], .stApp {
        background-color: #090A0F !important;
        color: #EDEDEF !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    .block-container {
        max-width: 1240px !important;
        padding-top: 1.75rem !important;
        padding-bottom: 3rem !important;
    }

    /* Top Navigation & Status Bar */
    .topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 1.1rem;
        margin-bottom: 1.5rem;
        border-bottom: 1px solid #1E2028;
    }
    .brand-wrap {
        display: flex;
        align-items: baseline;
        gap: 12px;
    }
    .brand-name {
        font-size: 1.05rem;
        font-weight: 600;
        color: #FFFFFF;
        letter-spacing: -0.02em;
    }
    .brand-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: #7E828E;
        border: 1px solid #232630;
        background: #11131A;
        padding: 2px 8px;
        border-radius: 4px;
    }
    .sys-pills {
        display: flex;
        gap: 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.74rem;
        color: #8A8F9E;
    }
    .sys-pill span {
        color: #E2E4E9;
        font-weight: 500;
    }
    .dot-live {
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background-color: #10B981;
        margin-right: 6px;
        vertical-align: middle;
    }

    /* Section Labels */
    .sec-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6E7381;
        margin-bottom: 0.6rem;
    }

    /* Surface Cards */
    .surface-card {
        background: #0E1016;
        border: 1px solid #1E2028;
        border-radius: 6px;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }
    .verdict-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 1rem;
        margin-bottom: 1rem;
        border-bottom: 1px solid #1A1C24;
    }
    .status-pill-pass {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.76rem;
        font-weight: 500;
        color: #10B981;
        background: rgba(16, 185, 129, 0.08);
        border: 1px solid rgba(16, 185, 129, 0.28);
        padding: 4px 10px;
        border-radius: 4px;
    }
    .status-pill-hold {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.76rem;
        font-weight: 500;
        color: #F59E0B;
        background: rgba(245, 158, 11, 0.08);
        border: 1px solid rgba(245, 158, 11, 0.28);
        padding: 4px 10px;
        border-radius: 4px;
    }

    /* KPI Grid */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-bottom: 1rem;
    }
    .kpi-box {
        background: #12141C;
        border: 1px solid #1E2028;
        border-radius: 5px;
        padding: 10px 12px;
    }
    .kpi-label {
        font-size: 0.7rem;
        color: #7E828E;
        margin-bottom: 4px;
    }
    .kpi-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.88rem;
        color: #F3F4F6;
        font-weight: 500;
    }

    /* Pipeline Walk */
    .walk-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 0.75rem 0;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
    }
    .walk-step {
        background: #141720;
        border: 1px solid #252836;
        color: #D1D5DB;
        padding: 3px 10px;
        border-radius: 4px;
    }
    .walk-arrow {
        color: #4B5060;
    }

    /* Policy Quote Box */
    .policy-quote {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.76rem;
        line-height: 1.55;
        color: #A1A7B5;
        background: #0B0C11;
        border-left: 2px solid #3B4052;
        padding: 8px 12px;
        margin-top: 6px;
        border-radius: 0 4px 4px 0;
    }

    /* Clean Inputs & Buttons */
    .stTextArea textarea, .stTextInput input, [data-baseweb="select"] > div {
        background-color: #0E1016 !important;
        border: 1px solid #222530 !important;
        color: #EDEDEF !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.82rem !important;
        border-radius: 5px !important;
    }
    .stButton > button {
        background-color: #EDEDEF !important;
        color: #090A0F !important;
        border: none !important;
        border-radius: 5px !important;
        font-weight: 500 !important;
        font-size: 0.82rem !important;
        padding: 0.5rem 1rem !important;
        transition: opacity 0.15s ease;
    }
    .stButton > button:hover {
        opacity: 0.9 !important;
    }
    div[data-testid="stTabs"] button {
        font-size: 0.82rem !important;
        color: #7E828E !important;
        font-weight: 500 !important;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #FFFFFF !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

LOG_PATH = ROOT_DIR / "logs" / "medclaim.jsonl" if (ROOT_DIR / "logs").exists() else Path("logs/medclaim.jsonl")


def fetch_rows(query: str) -> list[dict]:
    conn = connect()
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def read_traces() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    out = []
    for ln in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    return list(reversed(out))


# Ensure Strong-Room is stocked
if policy_collection().count() == 0:
    seed_db()
    seed_policy()

chroma_cnt = policy_collection().count()
prescriber_cnt = len(fetch_rows("SELECT * FROM prescribers"))
formulary_cnt = len(fetch_rows("SELECT * FROM formulary"))

# ---------------------------------------------------------------------------
# Minimalist Header Bar
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="topbar">
        <div class="brand-wrap">
            <span class="brand-name">MedClaim Rx</span>
            <span class="brand-tag">HEALTHCARE DOMAIN</span>
            <span class="brand-tag">v0.2.0</span>
        </div>
        <div class="sys-pills">
            <div class="sys-pill"><span class="dot-live"></span>Strong-Room <span>Online</span></div>
            <div class="sys-pill">COST_GATE <span>INR {COST_GATE:,.0f}</span></div>
            <div class="sys-pill">CONF_GATE <span>{CONF_GATE:.2f}</span></div>
            <div class="sys-pill">RAG Chunks <span>{chroma_cnt}</span></div>
            <div class="sys-pill">Registers <span>{prescriber_cnt} NMC / {formulary_cnt} Rx</span></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_workbench, tab_eval, tab_ledger, tab_gate = st.tabs(
    [
        "Triage Workbench",
        "Golden Benchmark (G01-G05)",
        "Audit Ledger & Registers",
        "Role & Permission Gate",
    ]
)

# ===========================================================================
# TAB 1: TRIAGE WORKBENCH
# ===========================================================================
with tab_workbench:
    left_col, right_col = st.columns([0.95, 1.25], gap="large")

    presets = {
        "G01 / Clean Standard Regimen (Amoxicillin 500mg)": CASES[0]["raw"],
        "G02 / High-Cost Biologic >= INR 25,000 (Adalimumab)": CASES[1]["raw"],
        "G03 / Unregistered NMC License (NMC-99INVALID)": CASES[2]["raw"],
        "G04 / Prompt Injection Override Attempt": CASES[3]["raw"],
        "G05 / Non-Formulary Experimental Compound": CASES[4]["raw"],
        "G06 / Incomplete Slip (Confidence < 0.80)": (
            "Prescriber: Dr. Sharma\nLicense: NMC-2019-4410\nDrug: RX-AMOX-500\nCost: 0"
        ),
    }

    with left_col:
        st.markdown('<div class="sec-label">01 / Prescription Input</div>', unsafe_allow_html=True)
        chosen = st.selectbox("Scenario Preset", list(presets.keys()), label_visibility="collapsed")

        c1, c2 = st.columns([2, 1])
        with c1:
            claim_id = st.text_input("Claim ID", value=f"CLM-{uuid.uuid4().hex[:6].upper()}", label_visibility="collapsed")
        with c2:
            if st.button("Reset DB", use_container_width=True):
                seed_db()
                seed_policy()
                st.rerun()

        raw_slip = st.text_area(
            "Prescription Slip Payload",
            value=presets[chosen],
            height=175,
            label_visibility="collapsed",
        )

        run_clicked = st.button("Execute Triage Graph", use_container_width=True)
        if run_clicked or "active_packet" not in st.session_state:
            st.session_state["active_packet"] = graph.invoke(
                {"claim_id": claim_id.strip() or "CLM-01", "raw_text": raw_slip, "trace": []}
            )

    with right_col:
        st.markdown('<div class="sec-label">02 / Deterministic Triage Output</div>', unsafe_allow_html=True)
        pkt = st.session_state["active_packet"]
        status = pkt.get("status", "unknown")
        gate = pkt.get("gate", "none")
        trace = pkt.get("trace", [])
        latency = pkt.get("latency_ms", 1.4)

        pill_cls = "status-pill-pass" if status == "ready_to_dispense" else "status-pill-hold"
        walk_html = '<span class="walk-arrow">→</span>'.join(
            [f'<span class="walk-step">{node}</span>' for node in trace]
        )

        hits_raw = pkt.get("policy_hits", "")
        if hits_raw:
            quotes_html = "".join([f'<div class="policy-quote">{q}</div>' for q in hits_raw.split(" | ")])
        else:
            quotes_html = '<div class="policy-quote">No policy chunks retrieved (stopped prior to RAG or empty collection).</div>'

        st.markdown(
            f"""
            <div class="surface-card">
                <div class="verdict-header">
                    <div>
                        <div class="kpi-label">DISPOSITION VERDICT</div>
                        <div style="font-size:1.05rem;font-weight:600;color:#FFF;">{status}</div>
                    </div>
                    <div class="{pill_cls}">gate: {gate}</div>
                </div>
                <div class="kpi-grid">
                    <div class="kpi-box">
                        <div class="kpi-label">Prescriber / NMC</div>
                        <div class="kpi-val">{pkt.get('prescriber') or '—'} ({pkt.get('license_no') or '—'})</div>
                    </div>
                    <div class="kpi-box">
                        <div class="kpi-label">Formulary Code</div>
                        <div class="kpi-val">{pkt.get('drug_code') or '—'}</div>
                    </div>
                    <div class="kpi-box">
                        <div class="kpi-label">Claim Amount</div>
                        <div class="kpi-val">INR {pkt.get('cost_inr', 0):,.2f}</div>
                    </div>
                    <div class="kpi-box">
                        <div class="kpi-label">Confidence / Latency</div>
                        <div class="kpi-val">{pkt.get('confidence', 0):.2f} / {latency}ms</div>
                    </div>
                </div>
                <div class="kpi-label">STATION TRACE</div>
                <div class="walk-row">{walk_html}</div>
                <div class="kpi-label" style="margin-top:1rem;">GROUNDED HANDBOOK EVIDENCE (CHROMADB)</div>
                {quotes_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("Inspect Raw ClaimPacket Contract (JSON)"):
            st.json(pkt)

# ===========================================================================
# TAB 2: GOLDEN BENCHMARK SUITE
# ===========================================================================
with tab_eval:
    st.markdown('<div class="sec-label">Regression Benchmark Suite (eval/run_golden.py)</div>', unsafe_allow_html=True)
    if st.button("Run Golden Suite (G01 - G05)"):
        results = []
        for case in CASES:
            out = graph.invoke({"claim_id": case["id"], "raw_text": case["raw"], "trace": []})
            passed = (out.get("status") == case["status"]) and (out.get("gate") == case["gate"])
            results.append(
                {
                    "ID": case["id"],
                    "Expected Status": case["status"],
                    "Actual Status": out.get("status"),
                    "Expected Gate": case["gate"],
                    "Actual Gate": out.get("gate"),
                    "Trace": " -> ".join(out.get("trace", [])),
                    "Result": "PASS" if passed else "FAIL",
                }
            )
        st.dataframe(results, use_container_width=True, hide_index=True)

# ===========================================================================
# TAB 3: AUDIT LEDGER & SQLITE REGISTERS
# ===========================================================================
with tab_ledger:
    st.markdown('<div class="sec-label">Append-Only JSONL Trace Diary (logs/medclaim.jsonl)</div>', unsafe_allow_html=True)
    traces = read_traces()
    if traces:
        st.dataframe(traces, use_container_width=True, hide_index=True)
    else:
        st.caption("No traces logged yet.")

    c_a, c_b, c_c = st.columns(3)
    with c_a:
        st.markdown('<div class="sec-label">SQLite: Prescribers</div>', unsafe_allow_html=True)
        st.dataframe(fetch_rows("SELECT * FROM prescribers"), use_container_width=True, hide_index=True)
    with c_b:
        st.markdown('<div class="sec-label">SQLite: Formulary</div>', unsafe_allow_html=True)
        st.dataframe(fetch_rows("SELECT * FROM formulary"), use_container_width=True, hide_index=True)
    with c_c:
        st.markdown('<div class="sec-label">SQLite: Persisted Claims</div>', unsafe_allow_html=True)
        st.dataframe(fetch_rows("SELECT claim_id, drug_code, cost_inr, status, gate FROM claims ORDER BY rowid DESC"), use_container_width=True, hide_index=True)

# ===========================================================================
# TAB 4: ROLE & PERMISSION GATE
# ===========================================================================
with tab_gate:
    st.markdown('<div class="sec-label">Deterministic 3-Tier Action Gate Simulator</div>', unsafe_allow_html=True)
    g1, g2, g3 = st.columns([2, 1, 1])
    with g1:
        cmd_input = st.text_input("Operator / Approver Command", value="Approve high-cost biologic override for RX-ADAL-40")
    with g2:
        role_input = st.selectbox("Active Role", ["operator", "cmo_approver"])
    with g3:
        cost_input = st.number_input("Associated Cost (INR)", value=68000.0, step=1000.0)

    gate_res = evaluate_action_gate(cmd_input, role=role_input, cost_inr=cost_input)
    route_cat = classify_request(cmd_input)
    st.json({"router_classification": route_cat, **gate_res})
