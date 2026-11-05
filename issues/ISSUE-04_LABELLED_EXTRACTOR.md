# Issue #04: Deterministic Labelled Slip Extractor & Sanitizer

**Label:** `nlp` `parsing` `data-sanitization`  
**Milestone:** Day 1 Foundation  
**Assignee:** Core Backend Agent  

---

## 📌 Context
Pharmacy clerks frequently enter prescription slips in semi-structured key-value formats. Before invoking any heavy LLM inference, we want a fast, zero-cost, deterministic Python parser that extracts core fields, sanitizes currency symbols, and assigns calibrated confidence metrics.

## 🎯 Requirements
1. Implement `app/extract_lab.py` with `parse_labelled(raw: str) -> dict`.
2. Extract fields:
   - Prescriber (`Doctor:`, `Prescriber:`, `Dr:`)
   - License (`License:`, `NMC:`, `Reg:`)
   - Drug Code (`Drug:`, `Rx:`, `Medication:`, `Code:`)
   - Diagnosis (`Diagnosis:`, `Indication:`, `Condition:`)
   - Cost (`Cost:`, `Amount:`, `Price:`, `Total:`)
3. Currency Sanitization:
   - Handle `₹`, `INR`, `Rs.`, commas (e.g. `₹30,000` -> `30000.0`).
   - Cleanly convert to float.
4. Confidence Scoring:
   - Cost present and valid: assign confidence `0.95`.
   - Cost missing or non-parseable: assign confidence `0.40`.
5. Versioned Prompt (`prompts/extract_v1.txt`):
   - Provide strict JSON extraction instructions for free-text prose slips, equipped with prompt injection safeguards.

## ✅ Acceptance Criteria
- Slips with `Cost: ₹28,500.00` correctly parse to `cost_inr = 28500.0`.
- Missing cost drops confidence to `0.40` (tripping `CONF_GATE`).
- Unit tests cover varied whitespace, currency symbols, and key aliases.
