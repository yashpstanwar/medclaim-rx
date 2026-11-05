"""Unit tests for ChromaDB Clinical Policy RAG Memory and fail-closed behavior."""

import unittest
import tempfile
import os
from pathlib import Path
from app.memory import (
    seed_policy,
    retrieve_policy_chunks,
    reset_policy_collection,
    DEFAULT_COLLECTION_NAME,
)


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.persist_dir = os.path.join(self.temp_dir.name, ".chroma")
        self.policy_path = os.path.join(self.temp_dir.name, "clinical_policy.md")

        # Create sample policy markdown file
        sample_policy = """# Clinical Policy Test Handbook
## Section 1: Prescriber Licensure
Prescription orders must be issued by a registered medical practitioner verified against the National Medical Commission (NMC) registry.
Unverified or unknown NMC medical licenses must stop immediately and be rejected without dispensing.

## Section 2: Biologics
Prescriptions costing ₹25,000 or more require a Chief Medical Officer stamp and countersignature prior to dispensing.
Specialty biologics falling under Tier 3 require explicit CMO prior-authorization.
"""
        with open(self.policy_path, "w", encoding="utf-8") as f:
            f.write(sample_policy)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_fail_closed_on_empty_shelf(self):
        # Empty collection must return [] without raising exceptions
        empty_collection_name = "empty_test_collection"
        chunks = retrieve_policy_chunks(
            query="biologic cost limit",
            persist_dir=self.persist_dir,
            collection_name=empty_collection_name,
        )
        self.assertEqual(chunks, [])

    def test_seed_and_retrieve_policy_chunks(self):
        collection_name = "test_clinical_policies"
        count = seed_policy(
            policy_path=self.policy_path,
            persist_dir=self.persist_dir,
            collection_name=collection_name,
        )
        self.assertEqual(count, 4)

        # Retrieve relevant rule
        chunks = retrieve_policy_chunks(
            query="Chief Medical Officer stamp 25000",
            persist_dir=self.persist_dir,
            collection_name=collection_name,
        )
        self.assertTrue(len(chunks) > 0)
        self.assertTrue(any("25,000" in chunk or "Chief Medical Officer" in chunk for chunk in chunks))

    def test_missing_policy_file_raises_error(self):
        with self.assertRaises(FileNotFoundError):
            seed_policy(
                policy_path="data/non_existent_policy.md",
                persist_dir=self.persist_dir,
            )


if __name__ == "__main__":
    unittest.main()
