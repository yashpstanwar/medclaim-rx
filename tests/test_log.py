"""Unit tests for PII-safe JSONL logger."""

import unittest
import tempfile
import json
from pathlib import Path
from app.log import write_trace, get_utc_timestamp


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

        # Crucial PII-safety assertion: raw text, patient name, Aadhaar must NEVER be logged
        self.assertNotIn("raw_text", record)
        self.assertNotIn("patient_name", record)
        self.assertNotIn("aadhaar", record)
        self.assertNotIn("diagnosis", record)


if __name__ == "__main__":
    unittest.main()
