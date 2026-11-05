# MedClaim Rx — Clinical Prior-Authorization & Formulary Desk

> **"MedClaim Rx clears routine clinical prescriptions same-day without recommending approval on an unverified prescriber NMC license, a non-formulary drug, or a skipped high-cost biologic stamp."**

---

## 🩺 System Overview

**MedClaim Rx** is a deterministic, clinical-grade Prior-Authorization and Formulary Verification Copilot for hospital pharmacies and Third-Party Administrators (TPAs). Designed with a **fail-closed** safety posture, MedClaim Rx ensures that every prescription claim undergoes strict registry validation, hospital formulary lookup, semantic clinical policy checking, and confidence-gated routing before any dispensing recommendation is issued.

### Key Pillars
- **Zero-Tolerance Prescriber Registry Verification:** Real-time National Medical Commission (NMC) verification against an authoritative SQLite strong-room. Unknown or unverified licenses halt approval instantly.
- **Formulary Conformance:** Checks active hospital drug formularies to block unapproved medications or redirect them to manual therapeutic substitution.
- **Biologic High-Cost Gate:** Prescriptions exceeding ₹25,000 INR deterministically require Chief Medical Officer (CMO) counter-signing.
- **Tri-Drawer Memory Model:**
  1. *Short-Term Working State:* Typed LangGraph `ClaimPacket` passing through functional nodes.
  2. *Semantic Clinical Policy Handbook:* Persistent ChromaDB vector index embedded with `sentence-transformers/all-MiniLM-L6-v2`.
  3. *Episodic Strong-Room & Audit Ledger:* ACID-compliant SQLite registers (`data/medclaim.db`) and non-repudiable JSONL logs (`logs/`).
- **Human-in-the-Loop Safeguard:** The system outputs recommendations only (`ready_to_dispense`, `cmo_review_needed`, `rejected_invalid`). Final dispensing authority remains strictly with the registered clinical pharmacist.

---

## 👥 Personas & Operational Roles

| Role | Operational Scope | Interaction Boundary |
| :--- | :--- | :--- |
| **Pharmacy Clerk** | Inputs intake prescription slips (labelled key-value or raw notes) | Submits slips; reviews triage status |
| **Clinical Pharmacist** | Conducts clinical reviews, therapeutic substitutions, and final sign-offs | Resolves formulary mismatches & low-confidence flags |
| **Insurance TPA** | Audits adjudications, policy hits, and financial clearance | Reviews trace audit logs and gate assertions |
| **Ops / CMO Lead** | High-cost authorization stamp (≥ ₹25,000 INR) & registry governance | Issues counter-signatures on flagged biologics |
