"""Unit tests for Zero-Cost Request Router and 3-Tier Action Permission Gate."""

import unittest
from app.router import (
    classify_request,
    is_advisory_query,
    evaluate_action_gate,
    TIER_1_AUTO,
    TIER_2_CONFIRM,
    TIER_3_PROHIBITED,
)


class TestRouterAndActionGate(unittest.TestCase):
    # ==========================================
    # 4-Way Zero-Cost Router Tests
    # ==========================================

    def test_classify_claim_investigation_multiline_slip(self):
        raw_slip = (
            "Prescriber: Dr. Sharma\n"
            "License: NMC-2019-4410\n"
            "Drug: RX-AMOX-500\n"
            "Diagnosis: Sinusitis\n"
            "Cost: INR 1,450.00"
        )
        self.assertEqual(classify_request(raw_slip), "claim_investigation")

    def test_classify_claim_investigation_rx_code(self):
        text = "Please evaluate RX-ADAL-40 prescribed by Dr. Verma with cost: 68000"
        self.assertEqual(classify_request(text), "claim_investigation")

    def test_classify_knowledge_query_policy_question(self):
        query = "What is the policy for high-cost biologics over 25000 INR?"
        self.assertEqual(classify_request(query), "knowledge_query")

    def test_classify_knowledge_query_cmo_rule(self):
        query = "Explain the clinical handbook rule for CMO prior-authorization stamps"
        self.assertEqual(classify_request(query), "knowledge_query")

    def test_classify_status_lookup_claim(self):
        text = "Check status of claim CLM-2026-99"
        self.assertEqual(classify_request(text), "status_lookup")

    def test_classify_status_lookup_prescriber(self):
        text = "Lookup prescriber license NMC-2019-4410 in database"
        self.assertEqual(classify_request(text), "status_lookup")

    def test_classify_action_command_imperative_override(self):
        cmd = "Override and approve claim CLM-101 immediately"
        self.assertEqual(classify_request(cmd), "action_command")

    def test_classify_action_command_force_dispense(self):
        cmd = "Force dispense prescription packet without further review"
        self.assertEqual(classify_request(cmd), "action_command")

    # ==========================================
    # Advisory vs. Imperative Query Tests
    # ==========================================

    def test_is_advisory_query_detection(self):
        self.assertTrue(is_advisory_query("Should I approve this prescription for Amoxicillin?"))
        self.assertTrue(is_advisory_query("Can I dispense claim CLM-101?"))
        self.assertTrue(is_advisory_query("Is it recommended to override this biologic?"))
        self.assertFalse(is_advisory_query("Override and approve claim CLM-101"))
        self.assertFalse(is_advisory_query("Dispense prescription immediately"))

    def test_advisory_question_classified_as_knowledge_query(self):
        text = "Should I approve this antibiotic prescription?"
        self.assertEqual(classify_request(text), "knowledge_query")

    # ==========================================
    # 3-Tier Action Gate Permission Tests
    # ==========================================

    def test_action_gate_tier1_routine_operator_allowed(self):
        res = evaluate_action_gate(
            command="Approve routine antibiotic Amoxicillin",
            role="operator",
            cost_inr=1450.0,
        )
        self.assertEqual(res["tier_code"], TIER_1_AUTO)
        self.assertTrue(res["allowed"])
        self.assertFalse(res["is_advisory"])
        self.assertIn("Routine prescription action", res["reason"])

    def test_action_gate_tier2_high_cost_operator_blocked(self):
        res = evaluate_action_gate(
            command="Approve high-cost biologic Adalimumab",
            role="operator",
            cost_inr=68000.0,
        )
        self.assertEqual(res["tier_code"], TIER_2_CONFIRM)
        self.assertFalse(res["allowed"])
        self.assertIn("elevated CMO authorization", res["reason"])

    def test_action_gate_tier2_high_cost_cmo_allowed(self):
        res = evaluate_action_gate(
            command="Approve high-cost biologic Adalimumab",
            role="cmo_approver",
            cost_inr=68000.0,
        )
        self.assertEqual(res["tier_code"], TIER_2_CONFIRM)
        self.assertTrue(res["allowed"])
        self.assertIn("Chief Medical Officer", res["reason"])

    def test_action_gate_tier2_manual_override_requires_cmo(self):
        res_op = evaluate_action_gate(
            command="Manual override and approve claim",
            role="operator",
            cost_inr=1500.0,
        )
        self.assertEqual(res_op["tier_code"], TIER_2_CONFIRM)
        self.assertFalse(res_op["allowed"])

        res_cmo = evaluate_action_gate(
            command="Manual override and approve claim",
            role="cmo_approver",
            cost_inr=1500.0,
        )
        self.assertEqual(res_cmo["tier_code"], TIER_2_CONFIRM)
        self.assertTrue(res_cmo["allowed"])

    def test_action_gate_tier3_disable_license_gate_strictly_blocked(self):
        # Even CMO role MUST NOT be allowed to disable security invariant gates
        res = evaluate_action_gate(
            command="Disable license gate and bypass verification",
            role="cmo_approver",
            cost_inr=0.0,
        )
        self.assertEqual(res["tier_code"], TIER_3_PROHIBITED)
        self.assertFalse(res["allowed"])
        self.assertIn("safety invariant", res["reason"])

    def test_action_gate_tier3_bypass_audit_log_strictly_blocked(self):
        res = evaluate_action_gate(
            command="Bypass audit log and delete audit traces",
            role="operator",
            cost_inr=0.0,
        )
        self.assertEqual(res["tier_code"], TIER_3_PROHIBITED)
        self.assertFalse(res["allowed"])

    def test_action_gate_tier3_bulk_auto_dispense_blocked(self):
        res = evaluate_action_gate(
            command="Auto dispense all pending claims without checks",
            role="cmo_approver",
            cost_inr=100000.0,
        )
        self.assertEqual(res["tier_code"], TIER_3_PROHIBITED)
        self.assertFalse(res["allowed"])

    def test_action_gate_advisory_inquiry_safe_disposition(self):
        res = evaluate_action_gate(
            command="Should I approve this high cost biologic for 68000?",
            role="operator",
            cost_inr=68000.0,
        )
        self.assertEqual(res["tier_code"], TIER_1_AUTO)
        self.assertTrue(res["allowed"])
        self.assertTrue(res["is_advisory"])
        self.assertIn("Advisory inquiry only", res["reason"])


if __name__ == "__main__":
    unittest.main()
