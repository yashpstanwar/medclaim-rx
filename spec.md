# MedClaim Rx — Product Specification & Clinical Rules

**Document Version:** 1.0.0  
**Status:** FROZEN  
**Target Platform:** Hospital Pharmacy Formulary Desk & TPA Prior-Authorization

---

## 1. Executive Summary & Job Statement

> **"MedClaim Rx clears routine clinical prescriptions same-day without recommending approval on an unverified prescriber NMC license, a non-formulary drug, or a skipped high-cost biologic stamp."**

MedClaim Rx operates as a safety-critical clinical copilot. It ingests prescription slips, enforces deterministic multi-tiered clinical gates, retrieves institutional policies via semantic vector memory, checks verified doctor registries, and produces verifiable routing decisions.

---

## 2. Scenario Freeze & Persona Matrix

The operational scope is frozen around four core hospital and insurance stakeholders:

| Persona | Primary Responsibilities | Allowed System Interactions | Out-of-Scope Privileges |
| :--- | :--- | :--- | :--- |
| **Pharmacy Clerk** | Front-desk Rx intake, preliminary key-value transcription, triage intake. | Submit raw/labelled Rx slips; inspect intake parse confidence; flag missing fields. | Cannot override doctor verification or approve claims. |
| **Clinical Pharmacist** | Clinical review, therapeutic substitution, drug-drug interaction check, final dispensation recommendation sign-off. | Review flagged/non-formulary claims; execute therapeutic substitution; validate dosage/duration. | Cannot bypass CMO authorization for high-cost biologics. |
| **Insurance TPA** | Prior-authorization adjudication, financial policy clearance, compliance audit. | Inspect claim packets, policy hit rationales, deterministic rule traces, and cost splits. | Cannot alter medical diagnoses or tamper with immutable ledger. |
| **Ops / CMO Lead** | Chief Medical Officer high-cost counter-signatory, registry governance, system oversight. | Provide biometric/digital counter-signature on claims ≥ ₹25,000 INR; update doctor license registries. | Cannot bypass audit trail logging. |

---

## 3. Allowed Data Sources

MedClaim Rx operates exclusively against authorized, locally verifiable, and deterministic data stores:

1. **Authoritative Prescriber Registry (`medclaim.db -> prescribers`):**
   - SQLite table containing National Medical Commission (NMC) registrations.
   - Required fields: `license_no` (Primary Key), `doctor_name`, `specialty`, `status` (`ACTIVE`, `SUSPENDED`, `REVOKED`), `state_council`.
2. **Hospital Formulary Register (`medclaim.db -> formulary`):**
   - SQLite table containing hospital-approved therapeutic agents.
   - Required fields: `drug_code` (Primary Key), `drug_name`, `category`, `tier` (1=Generic, 2=Preferred, 3=Specialty/Biologic), `is_formulary` (Boolean), `max_daily_dose`.
3. **Clinical Policy Handbook (`data/clinical_policy.md` -> ChromaDB):**
   - Institutional guidelines covering prior-authorization criteria, biologic thresholds, off-label therapeutic substitution policies, and emergency overrides.
4. **Episodic Audit Ledger (`medclaim.db -> claims` & `logs/audit_traces.jsonl`):**
   - Non-repudiable log of all processed claims, gate outcomes, semantic policy hits, and operator timestamps.

---

## 4. Success Criteria & Harm Mitigation

### 4.1 Success Criteria
- **Zero False Approvals on Licensure:** 0% rate of recommending approval when an NMC license is absent, unknown, or suspended.
- **Zero Formulary Violations:** 0% unverified approval of non-formulary medications without therapeutic substitution sign-off.
- **Zero High-Cost Biologic Stamp Bypass:** 100% of claims with `cost_inr >= 25000.0` correctly routed to `cmo_review_needed`.
- **Same-Day Routine Clearance:** Fully automated preliminary triage of routine formulary claims (< ₹25,000 INR, verified license, confidence ≥ 0.80) in under 2 seconds.

### 4.2 Harm Taxonomy & Mitigations

| Harm Type | Clinical / Operational Risk | Architectural Safeguard |
| :--- | :--- | :--- |
| **Direct Patient Harm** | Dispensation of toxic, contraindicated, or counterfeit drug | Strict formulary whitelist check; mandatory clinical pharmacist final human sign-off. |
| **Regulatory & Fraud Harm** | Quackery, prescription forging, suspended doctors issuing controlled drugs | Parameterized NMC license lookup against SQLite strong-room; immediate `rejected_invalid` halt. |
| **Financial Leakage** | Erroneous payment/clearance of expensive biologic drugs without pre-auth | Deterministic Python cost gate (`COST_GATE = 25000.0`) routing to `cmo_review_needed`. |
| **Privacy / PII Harm** | Exposure of patient identities, Aadhaar numbers, or sensitive conditions | PII minimization: strict omission of patient names/Aadhaar from logs; synthetic `claim_id` hashing. |
| **AI Hallucination Harm** | LLM fabricating policy exceptions or approving invalid claims | Hybrid state graph: deterministic Python gating overrides any LLM output; Chroma RAG strictly grounds rationale. |

---

## 5. Explicit Out-of-Scope Boundaries

To maintain absolute patient safety and regulatory compliance, the following capabilities are **strictly out of scope**:
1. **No Automated Robotic Dispensing:** The system shall never interface directly with robotic pill dispensers, IV compounders, or physical lockboxes.
2. **No Direct Bank / NEFT / UPI Financial Payouts:** The system outputs prior-authorization recommendation flags only; it never dispatches financial transfers or integrates with payment gateways.
3. **No Autonomous Prescribing / Clinical Diagnosis:** The system does not recommend clinical treatment courses or diagnose medical conditions from scratch.
4. **No Unsupervised Autonomous Approval:** `ready_to_dispense` is an advisory recommendation for the dispensing pharmacist, who retains statutory legal responsibility.
