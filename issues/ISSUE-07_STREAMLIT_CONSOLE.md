# Issue #07: Streamlit Clinical Reviewer Console & Audit Dashboard

**Label:** `ui` `streamlit` `observability` `dark-mode`  
**Milestone:** Day 2 Final Delivery  
**Assignee:** Frontend & Observability Lead  

---

## 📌 Context
Hospital pharmacists and TPA auditors require an intuitive, real-time interface to inspect prescription intake, observe deterministic LangGraph station executions, view semantic RAG evidence from ChromaDB, and audit the episodic SQLite ledger.

---

## 🎯 Requirements & Functional Layout

### 1. Visual Theme (Obsidian Dark-Mode)
- Background: `#0B0C10` (Obsidian Deep Dark)
- Accent / Pass Badges: `#00F0FF` (Electric Cyan)
- Review / Warning Badges: `#D4AF37` (Champagne Gold)
- Typography: Clean sans-serif with high contrast metric cards and glowing status pills.

### 2. Sidebar Navigation & Controls
- Displays deterministic Python gate constants: `COST_GATE = 25000.0 INR`, `CONF_GATE = 0.80`.
- Real-time inventory metrics: Live ChromaDB policy chunks count, registered doctors, and formulary medications.
- Interactive **"Re-Seed Strong-Room (DB + RAG)"** button to reset SQLite registers and re-index vector guidelines.

### 3. Multi-Tab Workflow Architecture
- **Tab 1: Live Prescription Triage Desk**
  - Left Column: Preset selector (G01 Clean, G02 High-Cost Biologic, G03 Bad License, G04 Prompt Injection, G05 Non-Formulary, G06 Low Confidence), Claim ID input, editable Rx text area, and "Invoke LangGraph Desk" action button.
  - Right Column: High-visibility Status Badge (`READY TO DISPENSE` vs `NEEDS PHARMACIST REVIEW`), 3-station pill walk (`extract` → `policy` → `route`), primary metrics (Cost INR, Confidence, Prompt Version), ChromaDB Retrieved Clinical Policy Evidence expander, and full JSON `ClaimPacket` dump.
- **Tab 2: Golden Set Exam (G01–G05)**
  - One-click regression benchmark runner executing all 5 frozen golden test cases through `graph.invoke()`.
  - Color-coded summary table displaying Case ID, Scenario, Expected vs Actual Status & Gate, and dynamic PASS/FAIL badges.
- **Tab 3: Observability & Strong-Room**
  - Interactive JSONL trace diary reading directly from `logs/medclaim.jsonl`.
  - Relational table viewer querying SQLite `claims`, `prescribers`, and `formulary` tables.
