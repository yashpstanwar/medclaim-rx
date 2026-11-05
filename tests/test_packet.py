"""Unit tests for ClaimPacket state contract."""

import unittest
from app.packet import ClaimPacket, create_claim_packet


class TestClaimPacket(unittest.TestCase):
    def test_create_default_claim_packet(self):
        packet = create_claim_packet()
        self.assertTrue(packet["claim_id"].startswith("CLM-"))
        self.assertEqual(packet["raw_text"], "")
        self.assertEqual(packet["prescriber"], "")
        self.assertEqual(packet["license_no"], "")
        self.assertEqual(packet["drug_code"], "")
        self.assertEqual(packet["diagnosis"], "")
        self.assertEqual(packet["cost_inr"], 0.0)
        self.assertEqual(packet["confidence"], 0.0)
        self.assertEqual(packet["status"], "pending")
        self.assertEqual(packet["gate"], "INTAKE")
        self.assertEqual(packet["policy_hits"], [])
        self.assertEqual(packet["trace"], ["INTAKE"])
        self.assertEqual(packet["prompt_version"], "v1.0")

    def test_create_custom_claim_packet(self):
        packet = create_claim_packet(
            claim_id="CLM-TEST-001",
            raw_text="Prescriber: Dr. Sharma\nCost: ₹1,500",
            prescriber="Dr. Sharma",
            license_no="NMC-2019-4410",
            drug_code="RX-AMOX-500",
            diagnosis="Bacterial Infection",
            cost_inr=1500.0,
            confidence=0.95,
            status="ready_to_dispense",
            gate="ROUTINE_CLEARANCE",
            policy_hits=["Hospital formulary approved"],
            trace=["INTAKE", "POLICY_CHECK", "ROUTE"],
            prompt_version="labelled_v1",
        )
        self.assertEqual(packet["claim_id"], "CLM-TEST-001")
        self.assertEqual(packet["prescriber"], "Dr. Sharma")
        self.assertEqual(packet["license_no"], "NMC-2019-4410")
        self.assertEqual(packet["cost_inr"], 1500.0)
        self.assertEqual(packet["confidence"], 0.95)
        self.assertEqual(packet["status"], "ready_to_dispense")
        self.assertEqual(packet["policy_hits"], ["Hospital formulary approved"])


if __name__ == "__main__":
    unittest.main()
