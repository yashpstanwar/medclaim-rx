"""Zero-Cost Request Router and 3-Tier Action Permission Gate for MedClaim Rx.

Provides deterministic, zero-LLM-cost routing and security enforcement:
  1. 4-Way Request Classification:
     - knowledge_query: Clinical handbook, policy, and guideline questions.
     - status_lookup: SQLite strong-room lookups for prescribers, formulary, or claims.
     - claim_investigation: Full 3-station LangGraph prior-authorization triage.
     - action_command: Imperative administrative commands and workflow overrides.

  2. 3-Tier Action Permission Gate:
     - Tier 1 (AUTOMATICALLY_ALLOWED): Routine actions & queries under ₹25,000.
     - Tier 2 (CONFIRMATION_REQUIRED): High-cost biologics (₹25k+) or manual overrides;
       requires Chief Medical Officer (cmo_approver) role.
     - Tier 3 (NEVER_PERMITTED): Safety invariant violations (e.g. disabling gates,
       bypassing audit logs, bulk unverified dispensing).
"""

import re
from typing import Dict, Any, List

ROUTER_CATEGORIES: List[str] = [
    "knowledge_query",
    "status_lookup",
    "claim_investigation",
    "action_command",
]

TIER_1_AUTO: str = "AUTOMATICALLY_ALLOWED"
TIER_2_CONFIRM: str = "CONFIRMATION_REQUIRED"
TIER_3_PROHIBITED: str = "NEVER_PERMITTED"

PROHIBITED_COMMAND_PATTERNS: List[str] = [
    "disable license gate",
    "disable gate",
    "disable verification",
    "bypass audit log",
    "bypass audit",
    "bypass log",
    "auto dispense all",
    "dispense all",
    "delete audit",
    "drop table",
    "delete claims",
    "ignore nmc",
    "ignore license",
    "skip formulary",
    "disable security",
]


def is_advisory_query(text: str) -> bool:
    """Detect whether user query is asking for advice/recommendation rather than issuing an imperative command.

    Examples:
      - 'Should I approve Amoxicillin for ₹1,450?' -> Advisory
      - 'Can I dispense this claim?' -> Advisory
      - 'Override and approve claim CLM-101' -> Imperative
    """
    clean = (text or "").strip().lower()
    advisory_prefixes = [
        "should i",
        "can i",
        "could i",
        "would it be",
        "is it recommended",
        "is it allowed",
        "do you recommend",
        "may i",
    ]
    return any(clean.startswith(prefix) for prefix in advisory_prefixes) or (
        clean.endswith("?") and any(word in clean for word in ["approve", "dispense", "override", "proceed"])
    )


def classify_request(text: str) -> str:
    """Classify incoming request into one of 4 deterministic routing paths with zero LLM cost.

    Returns:
        One of 'claim_investigation', 'action_command', 'status_lookup', or 'knowledge_query'.
    """
    clean = (text or "").strip()
    lower = clean.lower()

    if not clean:
        return "claim_investigation"

    # 1. Claim Investigation: Structured or semi-structured prescription slips
    slip_markers = [
        "license:", "licence:", "drug:", "prescriber:", "doctor:",
        "diagnosis:", "cost:", "rx-", "nmc-", "patient:"
    ]
    marker_hits = sum(1 for m in slip_markers if m in lower)
    if marker_hits >= 2 or ("rx-" in lower and ("cost:" in lower or "nmc" in lower or "dr." in lower)):
        return "claim_investigation"

    # 2. Action Command: Imperative state-changing instructions (non-advisory)
    action_verbs = [
        "override", "approve", "reject", "dispense", "force", "bypass",
        "disable", "delete", "clear", "cancel", "execute", "set status", "mark ready"
    ]
    advisory = is_advisory_query(clean)
    if not advisory:
        for verb in action_verbs:
            if lower.startswith(verb) or f" {verb} " in f" {lower} ":
                return "action_command"

    # 3. Status Lookup: Inspecting database records
    status_keywords = [
        "status of", "check status", "lookup", "is doctor", "is dr.", "is license",
        "find claim", "get claim", "verify prescriber", "check prescriber", "check license"
    ]
    if any(kw in lower for kw in status_keywords) or lower.startswith("check ") or lower.startswith("lookup "):
        return "status_lookup"

    # 4. Knowledge Query: Guidelines, thresholds, clinical handbook queries
    knowledge_keywords = [
        "what is", "what are", "policy", "handbook", "guideline", "rule", "threshold",
        "criteria", "when is", "how much", "tell me about", "explain", "who needs",
        "biologic rule", "cost gate", "cmo requirement"
    ]
    if any(kw in lower for kw in knowledge_keywords) or lower.endswith("?") or advisory:
        return "knowledge_query"

    return "claim_investigation"


def evaluate_action_gate(
    command: str,
    role: str = "operator",
    cost_inr: float = 0.0,
) -> Dict[str, Any]:
    """Evaluate a 3-tier deterministic action permission gate.

    Args:
        command: Command or question text submitted by user.
        role: User role ('operator' or 'cmo_approver').
        cost_inr: Claim cost in INR.

    Returns:
        Dictionary with keys:
          - tier: Human-readable tier label.
          - tier_code: AUTOMATICALLY_ALLOWED, CONFIRMATION_REQUIRED, or NEVER_PERMITTED.
          - allowed: Boolean flag indicating if action is permitted under current role.
          - role: The evaluated role.
          - is_advisory: True if question is advisory only (no mutation).
          - reason: Rationale for disposition.
          - recommendation: Actionable next step or advice.
    """
    clean_cmd = (command or "").strip()
    lower_cmd = clean_cmd.lower()
    advisory = is_advisory_query(clean_cmd)

    # Check Tier 3: NEVER_PERMITTED (Safety Invariants)
    for prohibited in PROHIBITED_COMMAND_PATTERNS:
        if prohibited in lower_cmd:
            return {
                "tier": "Tier 3: NEVER_PERMITTED",
                "tier_code": TIER_3_PROHIBITED,
                "allowed": False,
                "role": role,
                "is_advisory": advisory,
                "reason": f"Command violates core clinical safety invariant: '{prohibited}'.",
                "recommendation": "Hard security rejection. System audit alert triggered and recorded.",
            }

    # Advisory questions do not alter state
    if advisory:
        return {
            "tier": "Tier 1: AUTOMATICALLY_ALLOWED",
            "tier_code": TIER_1_AUTO,
            "allowed": True,
            "role": role,
            "is_advisory": True,
            "reason": "Advisory inquiry only; recommendation provided without state mutation.",
            "recommendation": "Review suggested guideline before issuing imperative commands.",
        }

    # Check Tier 2: CONFIRMATION_REQUIRED (High-cost biologics >= ₹25,000 or manual overrides)
    is_high_cost = cost_inr >= 25000.0
    is_override = any(kw in lower_cmd for kw in ["override", "force", "cmo", "waiver", "bypass"])

    if is_high_cost or is_override:
        if role == "cmo_approver":
            return {
                "tier": "Tier 2: CONFIRMATION_REQUIRED",
                "tier_code": TIER_2_CONFIRM,
                "allowed": True,
                "role": role,
                "is_advisory": False,
                "reason": "Authorized by Chief Medical Officer (cmo_approver) credential stamp.",
                "recommendation": "CMO electronic signature appended to audit ledger.",
            }
        else:
            return {
                "tier": "Tier 2: CONFIRMATION_REQUIRED",
                "tier_code": TIER_2_CONFIRM,
                "allowed": False,
                "role": role,
                "is_advisory": False,
                "reason": (
                    f"Action requires elevated CMO authorization "
                    f"({'Prescription cost ₹' + f'{cost_inr:,.2f}' + ' >= ₹25,000 threshold' if is_high_cost else 'Manual override requested'}). "
                    f"Current role '{role}' is restricted to routine desk operations."
                ),
                "recommendation": "Escalate claim to Chief Medical Officer queue for countersignature.",
            }

    # Tier 1: AUTOMATICALLY_ALLOWED (Routine operations under ₹25,000)
    return {
        "tier": "Tier 1: AUTOMATICALLY_ALLOWED",
        "tier_code": TIER_1_AUTO,
        "allowed": True,
        "role": role,
        "is_advisory": False,
        "reason": f"Routine prescription action within delegated operator authority (Cost: ₹{cost_inr:,.2f} < ₹25,000).",
        "recommendation": "Proceed with standard dispensing workflow.",
    }
