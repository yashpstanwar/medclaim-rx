"""Unit tests for FastAPI REST Service Wrapper."""

import unittest
from fastapi.testclient import TestClient
from app.api import app


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check_endpoint(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("status", data)
        self.assertEqual(data["service"], "MedClaim Rx Copilot API")
        self.assertTrue(data["sqlite_strong_room"]["connected"])
        self.assertTrue(data["chromadb_rag"]["connected"])

    def test_triage_clean_prescription_success(self):
        payload = {
            "raw_text": (
                "Prescriber: Dr. Sharma\n"
                "License: NMC-2019-4410\n"
                "Drug: RX-AMOX-500\n"
                "Diagnosis: Bacterial Sinusitis\n"
                "Cost: INR 1,450.00"
            ),
            "claim_id": "CLM-API-TEST-01",
        }
        res = self.client.post("/triage", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ready_to_dispense")
        self.assertEqual(data["gate"], "none")
        self.assertEqual(data["prescriber"], "Dr. Sharma")

    def test_triage_high_cost_biologic_routed_to_review(self):
        payload = {
            "raw_text": (
                "Doctor: Dr. Verma\n"
                "License: NMC-2016-8821\n"
                "Drug: RX-ADAL-40\n"
                "Diagnosis: Rheumatoid Arthritis\n"
                "Cost: INR 68,000.00"
            ),
        }
        res = self.client.post("/triage", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "needs_pharmacist_review")
        self.assertEqual(data["gate"], "high_cost_gate")

    def test_triage_silent_failure_empty_text_guard(self):
        res = self.client.post("/triage", json={"raw_text": "   "})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Silent-Failure Guard", res.json()["detail"])

    def test_action_gate_routine_allowed(self):
        payload = {
            "command": "Approve routine Amoxicillin",
            "role": "operator",
            "cost_inr": 1450.0,
        }
        res = self.client.post("/action-gate", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["tier_code"], "AUTOMATICALLY_ALLOWED")
        self.assertTrue(data["allowed"])

    def test_action_gate_cmo_override_allowed(self):
        payload = {
            "command": "Override and approve high cost biologic",
            "role": "cmo_approver",
            "cost_inr": 68000.0,
        }
        res = self.client.post("/action-gate", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["tier_code"], "CONFIRMATION_REQUIRED")
        self.assertTrue(data["allowed"])


if __name__ == "__main__":
    unittest.main()
