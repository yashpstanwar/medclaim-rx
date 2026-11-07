"""Unit tests for PII-safe JSONL logger and Token Cost Estimator."""

import unittest
import tempfile
import json
from pathlib import Path
from app.log import write_trace, get_utc_timestamp, estimate_token_cost


class TestLog(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_log_path = Path(self.temp_dir.name) / "test_medclaim.jsonl"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_utc_timestamp_format(self):
        ts = get_utc_timestamp()
        self.assertIsInstance(ts, str)
        self.assertIn("T", ts)

    def test_write_trace_creates_file_and_valid_json(self):
        packet = {
            "claim_id": "CLM-TEST-LOG-01",
            "prompt_version": "lab_labels_v1",
            "status": "ready_to_dispense",
            "gate": "none",
            "trace": ["extract", "policy", "route"],
            "cost_inr": 1450.0,
            "raw_text": "Patient Name: Secret Person, Aadhaar: 1234-5678-9012, Prescriber: Dr. Sharma",
            "patient_name": "John Doe",
            "aadhaar": "9999-8888-7777",
            "diagnosis": "Bacterial Sinusitis",
        }

        write_trace(packet, log_path=self.test_log_path)
        self.assertTrue(self.test_log_path.exists())

        with open(self.test_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])

        # Verify operational fields present
        self.assertEqual(record["claim_id"], "CLM-TEST-LOG-01")
        self.assertEqual(record["status"], "ready_to_dispense")
        self.assertEqual(record["gate"], "none")
        self.assertEqual(record["cost_inr"], 1450.0)
        self.assertEqual(record["trace"], ["extract", "policy", "route"])
        self.assertIn("ts", record)
        self.assertIn("latency_ms", record)
        self.assertIn("estimated_tokens", record)

        # Crucial PII-safety assertion: raw text, patient name, Aadhaar must NEVER be logged
        self.assertNotIn("raw_text", record)
        self.assertNotIn("patient_name", record)
        self.assertNotIn("aadhaar", record)
        self.assertNotIn("diagnosis", record)

    def test_estimate_token_cost_calculation(self):
        raw_text = "Prescriber: Dr. Sharma\nDrug: RX-AMOX-500\nCost: 1450"
        policy_hits = "Prescriptions require registered NMC practitioner."

        receipt = estimate_token_cost(raw_text, policy_hits)
        self.assertIn("prompt_tokens", receipt)
        self.assertIn("completion_tokens", receipt)
        self.assertIn("total_tokens", receipt)
        self.assertEqual(receipt["deterministic_cost_usd"], 0.0)
        self.assertEqual(receipt["local_llamacpp_cost_usd"], 0.0)
        self.assertGreater(receipt["groq_cost_usd"], 0.0)
        self.assertEqual(receipt["total_tokens"], receipt["prompt_tokens"] + receipt["completion_tokens"])

    def test_estimate_token_cost_empty_input(self):
        receipt = estimate_token_cost("", "")
        self.assertGreater(receipt["prompt_tokens"], 0)
        self.assertGreater(receipt["total_tokens"], 0)
        self.assertEqual(receipt["deterministic_cost_usd"], 0.0)

    def test_write_trace_explicit_latency_ms(self):
        packet = {
            "claim_id": "CLM-LATENCY-TEST",
            "prompt_version": "lab_labels_v1",
            "status": "ready_to_dispense",
            "gate": "none",
            "trace": ["extract", "policy", "route"],
            "cost_inr": 1200.0,
            "latency_ms": 2.456,
            "estimated_tokens": 85,
        }

        write_trace(packet, log_path=self.test_log_path)
        with open(self.test_log_path, "r", encoding="utf-8") as f:
            record = json.loads(f.readline())

        self.assertEqual(record["latency_ms"], 2.456)
        self.assertEqual(record["estimated_tokens"], 85)


if __name__ == "__main__":
    unittest.main()
