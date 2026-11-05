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
