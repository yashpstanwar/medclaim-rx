# MedClaim Rx — Claude Code Project Context & UI Polish Guide

> **Target Audience:** Claude Code CLI agent / autonomous developer.
> **Scope:** UI polish, frontend refinement, and user experience enhancements for the MedClaim Rx Streamlit console without breaking core LangGraph invariants, SQLite tools, or regression benchmarks.

---

## 1. Executive Summary & LMS Domain Requirements

- **Selected Capstone Domain:** `Healthcare domain` (mandatory for LMS submission compliance).
- **Project Title:** `MedClaim Rx — Clinical Prior-Authorization & Formulary Desk`.
- **Repository:** `https://github.com/yashpstanwar/medclaim-rx.git` (Active branch: `main`).
- **Live Deployment:** `https://medclaim-rx.streamlit.app/`.
- **One-Sentence Mission:** Clears routine clinical prescriptions same-day without recommending approval on an unverified prescriber NMC license, a non-formulary drug, or a skipped high-cost biologic stamp.
- **Verification Status:** 56/56 Pytest unit tests passing, 5/5 Golden Set regression cases passing (100% compliance).

---

## 2. Repository Architecture & Directory Tree

```
medclaim-rx/
├── app/
│   ├── __init__.py
│   ├── api.py             # FastAPI REST endpoints (/health, /triage, /action-gate)
│   ├── extract_lab.py     # Deterministic regex extraction & prompt_versioning
│   ├── graph.py           # LangGraph 3-station workflow (extract -> policy -> route)
│   ├── log.py             # PII-safe JSONL audit logger (logs/medclaim.jsonl)
│   ├── memory.py          # ChromaDB clinical RAG + fail-closed in-memory fallback
│   ├── packet.py          # Pydantic v2 ClaimPacket schema & state contracts
│   ├── router.py          # Zero-cost 4-way router & deterministic 3-tier action gate
│   ├── tools.py           # SQLite strong-room helpers (prescribers, formulary, claims)
│   └── ui.py              # Main interactive Streamlit Console (Current active UI)
├── data/
│   ├── clinical_policy.md # Authoritative clinical prior-authorization guidelines
│   └── medclaim.db        # SQLite relational strong-room database
├── eval/
│   ├── __init__.py
│   └── run_golden.py      # Golden benchmark harness for frozen cases G01–G05
├── logs/
│   └── medclaim.jsonl     # Append-only operational trace ledger (strictly no PII)
├── prompts/
│   ├── extract_v1.txt     # Baseline extraction prompt
│   └── extract_v2.txt     # Few-shot extraction prompt
├── tests/                 # 56 class-based pytest unit test suites
│   ├── test_api.py
│   ├── test_extract_lab.py
│   ├── test_graph.py
│   ├── test_log.py
│   ├── test_memory.py
│   ├── test_packet.py
│   ├── test_router.py
│   ├── test_security.py
│   └── test_tools.py
├── architecture.md        # Architecture specification with Mermaid sequence diagrams
├── spec.md                # System specification, frozen scenarios, and data boundaries
├── requirements.txt       # Production dependencies
├── streamlit_app.py       # Root Streamlit Cloud entrypoint wrapper
└── CLAUDE.md              # THIS FILE (Context & instructions for Claude Code)
```

---

## 3. Current UI Architecture (`app/ui.py`)

The active interface in `app/ui.py` is the **Obsidian High-Contrast Dark-Mode Clinical Console**:

### Visual Palette & Obsidian Dark Theme
- **Background (`.stApp`):** `#0B0C10` (Deep obsidian black).
- **Secondary Surfaces:** `#12141A` and `#1F2833` (Graphite / slate dark containers).
- **Electric Cyan (`#00F0FF` / `#66FCF1`):** Headers, pass badges (`.badge-pass`), station execution trace pills (`.station-pill`), metric values.
- **Champagne Gold (`#D4AF37` / `#FFD700`):** Review required badges (`.badge-review`), clinical hold flags.
- **Coral Red (`#FF4B4B`):** Danger / prohibited tier badges (`.badge-danger`).
- **Muted Gray (`#C5C6C7` / `#7E828E`):** Secondary labels, captions, metadata.

### UI Components & Navigation
1. **Sidebar (`st.sidebar`):**
   - **LMS Domain Pill:** High-visibility badge declaring `Domain: Healthcare | Live Capstone Build` (essential for graders).
   - **User Persona Selector:** Switch between `Operator (Clerk)` and `CMO Approver (Doctor)` to test role-based action gate permissions.
   - **Deterministic Python Gates:** Displays `COST_GATE = ₹25,000` and `CONF_GATE = 0.80`.
   - **Token Cost & Latency Receipt:** Latency ~1–2ms, zero-cost routing `$0.00`.
   - **Strong-Room Counters:** Live SQLite row counts (`prescribers`, `formulary`, `claims`) and ChromaDB policy chunk count.
   - **Re-Seed Strong-Room Button:** Triggers `seed_db()` and `seed_policy()` on click.

2. **Tab 1: Live Prescription Triage Desk:**
   - **Left Column:** Scenario preset selectbox (`G01`–`G06`), custom Claim ID input, editable raw prescription text area, live Zero-Cost Router preview chip, and primary execution button (`Invoke LangGraph Desk`).
   - **Right Column:** Triage Disposition Verdict banner (`READY TO DISPENSE` vs `NEEDS PHARMACIST REVIEW`), station execution trace walk (`EXTRACT` → `POLICY` → `ROUTE`), 4-metric grid (Cost, Confidence, Latency, Route Path), prescriber and medication summaries, ChromaDB retrieved policy hits expander, interactive 3-Tier Action Gate simulator, and raw `ClaimPacket` JSON inspector.

3. **Tab 2: Golden Set Benchmark Exam (G01–G05):**
   - Interactive runner executing the 5 frozen regression cases against the pipeline.
   - Shows live score card (5/5, 100%), summary table, and pass/fail indicators.

4. **Tab 3: Observability & Strong-Room Ledger:**
   - Latency and cost-avoidance metrics.
   - Sub-tab 1: Recent entries from `logs/medclaim.jsonl` (guarantees zero PII).
   - Sub-tab 2: Relational database explorer querying `claims`, `prescribers`, and `formulary` tables.

5. **Tab 4: Architecture & Sequence Flow:**
   - Embedded Mermaid sequence diagram illustrating the end-to-end message flow across Operator, Guard, Router, RAG, Tools, Gate, and Store.

---

## 4. Critical Invariants & Rules (DO NOT BREAK)

When polishing or refining the UI, Claude Code must adhere strictly to these non-negotiable architectural invariants:

### Invariant 1: Streamlit Cloud `sys.path` Anchor
Streamlit Community Cloud runs apps inside `/mount/src/medclaim-rx/app`. If `ROOT_DIR` is not prepended to `sys.path` at the very top of `app/ui.py`, Python cannot find the `app` package and crashes with `ModuleNotFoundError: No module named 'app'`.
**Requirement:** Lines 13–16 of `app/ui.py` MUST remain at the very top before any project imports:
```python
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
```

### Invariant 2: Explicit Status & Gate String Literals
All unit tests and golden benchmarks assert exact lowercase string values for triage outcomes:
- `status`: MUST be `"ready_to_dispense"` or `"needs_pharmacist_review"`. (Never change to `"approved"`, `"review"`, or `"passed"`).
- `gate`: MUST be `"none"`, `"high_cost_gate"`, `"license_mismatch"`, `"non_formulary"`, or `"low_confidence"`.
- `COST_GATE = 25000.0` (biologics $\ge$ ₹25,000 require CMO approval).
- `CONF_GATE = 0.80` (confidence $< 0.80$ routes to review).

### Invariant 3: Type-Safe `policy_hits` Normalization
In `app/packet.py`, `ClaimPacket` defines `policy_hits` as a `list[str]`. In certain mock or serialised states, it may be a `str` or `None`.
**Requirement:** NEVER call `.split()` directly on `pkt.get("policy_hits")`. Always normalize safely:
```python
hits = result.get("policy_hits")
if isinstance(hits, list):
    hits_list = [str(h).strip() for h in hits if str(h).strip()]
elif isinstance(hits, str):
    hits_list = [q.strip() for q in hits.split(" | ") if q.strip()]
else:
    hits_list = []
```

### Invariant 4: PII-Safe Logging
Never write raw clinical notes, patient names, Aadhaar numbers, or unmasked patient IDs to `logs/medclaim.jsonl`. Only write operational telemetry: `ts`, `claim_id`, `prompt_version`, `status`, `gate`, `trace`, `latency_ms`, `cost_inr`.

### Invariant 5: LMS Capstone Healthcare Domain Visibility
The grader must immediately identify that this repository is built for the **Healthcare domain**. Keep the Healthcare Domain badge visibly anchored in both the sidebar and main header.

---

## 5. Frozen Golden Benchmark Test Cases (Reference)

| Case ID | Prescriber / License | Drug Code | Cost (INR) | Expected Status | Expected Gate | Key Invariant Tested |
|---|---|---|---|---|---|---|
| **G01_CLEAN** | Dr. Sharma / NMC-2019-4410 | RX-AMOX-500 | ₹1,450 | `ready_to_dispense` | `none` | Clean clearance of routine antibiotic |
| **G02_HIGH_BIOLOGIC** | Dr. Verma / NMC-2016-8821 | RX-ADAL-40 | ₹68,000 | `needs_pharmacist_review` | `high_cost_gate` | High-cost biologic $\ge$ ₹25,000 gate |
| **G03_BAD_LICENSE** | Dr. Ghost / NMC-99INVALID | RX-AMOX-500 | ₹900 | `needs_pharmacist_review` | `license_mismatch` | Unverified prescriber license fails-closed |
| **G04_PROMPT_INJECT** | Dr. Verma / NMC-2016-8821 | RX-ADAL-40 | ₹75,000 | `needs_pharmacist_review` | `high_cost_gate` | Prompt injection fails to override cost gate |
| **G05_NON_FORMULARY** | Dr. Sharma / NMC-2019-4410 | RX-EXPERIMENTAL-99 | ₹4,200 | `needs_pharmacist_review` | `non_formulary` | Unapproved drug rejected by formulary tool |

---

## 6. Recent History & Lessons Learned

1. **Attempted Minimalist Redesign (Why it was reverted):**
   - A previous prompt attempted a complete rewrite that hid the sidebar, removed all emojis, and condensed the UI into a single page.
   - The user preferred the richer, multi-tab Obsidian console with the sidebar, live metrics, and interactive governance features intact.
   - Any polish should **enhance and refine** the existing Obsidian multi-tab console rather than gutting the sidebar or altering the core layout.

2. **Streamlit Preset Reactivity:**
   - In Streamlit, when a user selects a preset from `st.selectbox`, the `st.text_area` only reflects the change if keyed dynamically (e.g. `key=f"rx_input_{selected_preset}"`) or if updated through `st.session_state`.
   - Consider auto-running `graph.invoke()` when switching presets if the user desires instant card updates.

3. **Button Hierarchy Styling:**
   - Streamlit buttons default to secondary styling unless `type="primary"` is set.
   - Recommended hierarchy:
     - Primary Action (`type="primary"`): `Invoke LangGraph Desk` (Tab 1), `Execute Full Golden Set Exam` (Tab 2).
     - Secondary Action (default): `Re-Seed Strong-Room` (Sidebar), table filters, export actions.

---

## 7. Recommended UI Polish Tasks for Claude Code

If tasked with polishing the UI, focus on these high-value areas:
1. **Typography & Layout Cleanliness:**
   - Refine CSS spacing, margins, and card padding.
   - Ensure clean mono-spaced typography (`JetBrains Mono`, `Fira Code`, or `SF Mono`) for codes (`NMC-*`, `RX-*`), costs (`₹*`), and trace station walks.
2. **Interactive Visual Feedback:**
   - Add clear status indicators on the Action Gate simulator (showing green for permitted, amber for CMO required, red for strictly forbidden).
   - Ensure evidence quotes from ChromaDB display with readable blockquote styling and chunk indices.
3. **Dataframe & Table Presentation:**
   - Style the SQLite table explorer and JSONL trace table in Tab 3 with clean column headers and responsive widths (`use_container_width=True`).
4. **Preserve All Tests:**
   - Never remove or alter functions imported by test suites or benchmarks (`graph`, `COST_GATE`, `CONF_GATE`, `create_claim_packet`, `seed_db`, `seed_policy`, `evaluate_action_gate`, `classify_request`).

---

## 8. Verification & Test Commands

Before committing any UI modifications, run these commands to guarantee zero regression:

```bash
# 1. Run full 56-test pytest suite
PYTHONPATH=. pytest -v

# 2. Run the 5 frozen Golden Cases
PYTHONPATH=. python -m eval.run_golden

# 3. Dry-run UI imports & execution without launching a browser
python -c "import sys; from unittest.mock import MagicMock; mock_st = MagicMock(); mock_st.tabs.side_effect = lambda tabs, *a, **k: [MagicMock() for _ in tabs]; mock_st.columns.side_effect = lambda spec, *a, **k: [MagicMock() for _ in range(len(spec) if isinstance(spec, (list, tuple)) else spec)]; mock_st.selectbox.side_effect = lambda label, options, *a, **k: options[0]; mock_st.button.return_value = False; mock_st.text_input.return_value = 'CLM-01'; mock_st.text_area.return_value = 'sample'; mock_st.number_input.return_value = 68000.0; mock_st.session_state = {}; sys.modules['streamlit'] = mock_st; import app.ui; print('UI verified successfully!')"

# 4. Git status check
git status
```
