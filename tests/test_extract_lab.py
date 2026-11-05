"""Unit tests for deterministic labelled prescription slip extractor."""

import unittest
from app.extract_lab import parse_labelled, sanitize_currency, parse_to_packet


class TestExtractLab(unittest.TestCase):
    def test_sanitize_currency_variations(self):
        self.assertEqual(sanitize_currency("₹30,000"), 30000.0)
        self.assertEqual(sanitize_currency("₹ 1,500.50"), 1500.5)
        self.assertEqual(sanitize_currency("Rs. 25,000/-"), 25000.0)
        self.assertEqual(sanitize_currency("INR 450.00"), 450.0)
        self.assertEqual(sanitize_currency("28500"), 28500.0)
        self.assertIsNone(sanitize_currency(""))
        self.assertIsNone(sanitize_currency("N/A"))

    def test_parse_valid_labelled_slip(self):
        raw = """
        Prescriber: Dr. Sharma
        License: NMC-2019-4410
        Drug: RX-AMOX-500
        Diagnosis: Acute Sinusitis
        Cost: ₹1,500.00
        """
        result = parse_labelled(raw)
        self.assertEqual(result["prescriber"], "Dr. Sharma")
        # Ensure 'License: NMC-...' maps to 'license_no'
        self.assertEqual(result["license_no"], "NMC-2019-4410")
        # Ensure 'Drug: RX-...' maps to 'drug_code'
        self.assertEqual(result["drug_code"], "RX-AMOX-500")
        self.assertEqual(result["diagnosis"], "Acute Sinusitis")
        self.assertEqual(result["cost_inr"], 1500.0)
        self.assertEqual(result["confidence"], 0.95)
        # Ensure prompt_version is 'lab_labels_v1'
        self.assertEqual(result["prompt_version"], "lab_labels_v1")

    def test_parse_high_cost_biologic_slip(self):
        raw = """
        Doctor: Dr. Verma
        Reg No: NMC-2016-8821
        Medication: RX-ADAL-40
        Indication: Severe Rheumatoid Arthritis
        Amount: ₹ 35,000.00
        """
        result = parse_labelled(raw)
        self.assertEqual(result["prescriber"], "Dr. Verma")
        self.assertEqual(result["license_no"], "NMC-2016-8821")
        self.assertEqual(result["drug_code"], "RX-ADAL-40")
        self.assertEqual(result["cost_inr"], 35000.0)
        self.assertEqual(result["confidence"], 0.95)
        self.assertEqual(result["prompt_version"], "lab_labels_v1")

    def test_parse_missing_cost_drops_confidence(self):
        raw = """
        Prescriber: Dr. Sharma
        License: NMC-2019-4410
        Drug: RX-AMOX-500
        Diagnosis: Streptococcal Pharyngitis
        """
        result = parse_labelled(raw)
        self.assertEqual(result["cost_inr"], 0.0)
        self.assertEqual(result["confidence"], 0.40)
        self.assertEqual(result["prompt_version"], "lab_labels_v1")

    def test_parse_empty_string(self):
        result = parse_labelled("")
        self.assertEqual(result["prescriber"], "")
        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(result["prompt_version"], "lab_labels_v1")

    def test_parse_to_packet_helper(self):
        raw = """
        Prescriber: Dr. Sharma
        License: NMC-2019-4410
        Drug: RX-AMOX-500
        Cost: ₹2,000
        """
        packet = parse_to_packet(raw, claim_id="CLM-UNIT-100")
        self.assertEqual(packet["claim_id"], "CLM-UNIT-100")
        self.assertEqual(packet["license_no"], "NMC-2019-4410")
        self.assertEqual(packet["drug_code"], "RX-AMOX-500")
        self.assertEqual(packet["cost_inr"], 2000.0)
        self.assertEqual(packet["confidence"], 0.95)
        self.assertEqual(packet["prompt_version"], "lab_labels_v1")
        self.assertIn("EXTRACT_LABELLED", packet["trace"])


if __name__ == "__main__":
    unittest.main()
