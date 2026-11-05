# Issue #03: SQLite Clinical Strong-Room & Parameterized Tools

**Label:** `database` `sqlite` `security`  
**Milestone:** Day 1 Foundation  
**Assignee:** Core Backend Agent  

---

## 📌 Context
Prescriber verification and formulary validation require zero-tolerance deterministic lookups. Relational SQLite provides an ACID-compliant local strong-room that resists prompt injection and network jitter.

## 🎯 Requirements
1. Implement `app/tools.py` with a SQLite connection manager (`data/medclaim.db`) with `sqlite3.Row` factory.
2. Implement schema definition and seeding function `seed_db(db_path: str)`:
   - `prescribers`: `license_no` (PK), `doctor_name`, `specialty`, `status`, `created_at`
   - `formulary`: `drug_code` (PK), `drug_name`, `category`, `tier`, `is_formulary`, `requires_cmo`
   - `claims`: `claim_id` (PK), `prescriber`, `license_no`, `drug_code`, `cost_inr`, `status`, `gate`, `created_at`
3. Seed authoritative test records:
   - Verified Prescribers:
     - `Dr. Sharma` with `NMC-2019-4410` (ACTIVE)
     - `Dr. Verma` with `NMC-2016-8821` (ACTIVE)
     - *Important:* Do NOT seed `NMC-99INVALID` (must fail lookup).
   - Formulary Drugs:
     - `RX-AMOX-500` (Amoxicillin 500mg, Tier 1, is_formulary=1, requires_cmo=0)
     - `RX-ADAL-40` (Adalimumab 40mg, Tier 3 Biologic, is_formulary=1, requires_cmo=1)
4. Implement parameterized lookup tools:
   - `check_license(license_no: str) -> dict | None`
   - `lookup_formulary(drug_code: str) -> dict | None`
   - `save_claim(packet: ClaimPacket) -> bool`

## ✅ Acceptance Criteria
- Strictly parameterized SQL with `?` bindings.
- `check_license("NMC-2019-4410")` returns doctor dictionary with status `ACTIVE`.
- `check_license("NMC-99INVALID")` returns `None`.
- `lookup_formulary("RX-AMOX-500")` returns formulary metadata.
