"""Unit tests for SQLite strong-room and parameterized lookup tools."""

import unittest
import tempfile
import os
from pathlib import Path
from app.tools import (
    get_db_connection,
    seed_db,
    check_license,
    lookup_formulary,
    save_claim,
)
from app.packet import create_claim_packet


class TestTools(unittest.TestCase):
    def setUp(self):
        # Create an isolated temporary database for each test
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_medclaim.db")
        seed_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_tables_created(self):
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]
        conn.close()

        self.assertIn("prescribers", tables)
        self.assertIn("formulary", tables)
        self.assertIn("claims", tables)

    def test_check_license_verified_prescribers(self):
        # Dr. Sharma - returns 'KNOWN:...'
        doc1 = check_license("NMC-2019-4410", db_path=self.db_path)
        self.assertTrue(doc1.startswith("KNOWN:"))
        self.assertEqual(doc1, "KNOWN:Dr. Sharma")
        self.assertEqual(doc1["doctor_name"], "Dr. Sharma")
        self.assertEqual(doc1["status"], "ACTIVE")

        # Dr. Verma - returns 'KNOWN:...'
        doc2 = check_license("NMC-2016-8821", db_path=self.db_path)
        self.assertTrue(doc2.startswith("KNOWN:"))
        self.assertEqual(doc2, "KNOWN:Dr. Verma")
        self.assertEqual(doc2["doctor_name"], "Dr. Verma")
        self.assertEqual(doc2["status"], "ACTIVE")

    def test_check_license_unregistered_mismatch_fails(self):
        # NMC-99INVALID must NOT be seeded and must return UNKNOWN
        doc_invalid = check_license("NMC-99INVALID", db_path=self.db_path)
        self.assertEqual(doc_invalid, "UNKNOWN")

        # Blank or empty returns UNKNOWN
        self.assertEqual(check_license("", db_path=self.db_path), "UNKNOWN")

    def test_lookup_formulary_drugs(self):
        # Amoxicillin (Tier 1, standard) - returns 'FOUND:...'
        amox = lookup_formulary("RX-AMOX-500", db_path=self.db_path)
        self.assertTrue(amox.startswith("FOUND:"))
        self.assertEqual(amox["tier"], 1)
        self.assertEqual(amox["is_formulary"], 1)
        self.assertEqual(amox["requires_cmo"], 0)

        # Adalimumab (Tier 3, Biologic requiring CMO) - returns 'FOUND:...'
        adal = lookup_formulary("RX-ADAL-40", db_path=self.db_path)
        self.assertTrue(adal.startswith("FOUND:"))
        self.assertEqual(adal["tier"], 3)
        self.assertEqual(adal["requires_cmo"], 1)

    def test_lookup_formulary_unlisted_drug_fails(self):
        # Missing drug returns 'MISSING'
        unlisted = lookup_formulary("RX-UNKNOWN-999", db_path=self.db_path)
        self.assertEqual(unlisted, "MISSING")
        self.assertEqual(lookup_formulary("", db_path=self.db_path), "MISSING")

    def test_save_claim_persistence(self):
        packet = create_claim_packet(
            claim_id="CLM-TEST-PERSIST-1",
            raw_text="Prescriber: Dr. Sharma\nCost: ₹1,500",
            prescriber="Dr. Sharma",
            license_no="NMC-2019-4410",
            drug_code="RX-AMOX-500",
            diagnosis="Sinusitis",
            cost_inr=1500.0,
            confidence=0.95,
            status="ready_to_dispense",
            gate="ROUTINE_CLEARANCE",
            policy_hits=["Formulary standard match"],
            trace=["INTAKE", "POLICY_NODE", "ROUTE_NODE"],
        )

        success = save_claim(packet, db_path=self.db_path)
        self.assertTrue(success)

        # Verify claim exists in SQLite
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM claims WHERE claim_id = ?", ("CLM-TEST-PERSIST-1",))
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row["prescriber"], "Dr. Sharma")
        self.assertEqual(row["cost_inr"], 1500.0)
        self.assertEqual(row["status"], "ready_to_dispense")


if __name__ == "__main__":
    unittest.main()
