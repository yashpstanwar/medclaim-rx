"""Unit tests for LangGraph 3-station workflow execution."""

import unittest
from app.graph import graph
from app.packet import create_claim_packet


class TestGraph(unittest.TestCase):
    def test_clean_clearance_routing(self):
        # Routine Amoxicillin slip: Dr. Sharma, NMC-2019-4410, Cost ₹1,450
        raw = """
        Prescriber: Dr. Sharma
        License: NMC-2019-4410
        Drug: RX-AMOX-500
        Diagnosis: Bacterial Sinusitis
        Cost: ₹1,450.00
        """
        input_packet = create_claim_packet(raw_text=raw, claim_id="CLM-TEST-GRAPH-01")
        output = graph.invoke(input_packet)

        self.assertEqual(output["status"], "ready_to_dispense")
        self.assertEqual(output["gate"], "none")
        self.assertEqual(output["cost_inr"], 1450.0)
        self.assertEqual(output["trace"], ["extract", "policy", "route"])

    def test_low_confidence_rejection_needs_typecheck(self):
        # Missing cost drops extraction confidence to 0.40 (< 0.80 CONF_GATE)
        raw = """
        Prescriber: Dr. Sharma
        License: NMC-2019-4410
        Drug: RX-AMOX-500
        Diagnosis: Streptococcal Pharyngitis
        """
        input_packet = create_claim_packet(raw_text=raw, claim_id="CLM-TEST-GRAPH-02")
        output = graph.invoke(input_packet)

        self.assertEqual(output["status"], "needs_pharmacist_review")
        self.assertEqual(output["gate"], "needs_typecheck")
        self.assertEqual(output["trace"], ["extract", "policy", "route"])

    def test_trace_station_sequence(self):
        raw = """
        Prescriber: Dr. Sharma
        License: NMC-2019-4410
        Drug: RX-AMOX-500
        Cost: ₹500
        """
        input_packet = create_claim_packet(raw_text=raw)
        output = graph.invoke(input_packet)
        self.assertEqual(output["trace"], ["extract", "policy", "route"])


if __name__ == "__main__":
    unittest.main()
