"""Unit tests for ChromaDB Clinical Policy RAG Memory, Synonym Expansion, and Threshold Filtering."""

import unittest
import tempfile
import os
from pathlib import Path
from app.memory import (
    seed_policy,
    retrieve_policy_chunks,
    reset_policy_collection,
    expand_query_synonyms,
    CLINICAL_SYNONYMS,
    DEFAULT_THRESHOLD,
    STRICT_THRESHOLD,
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

    def test_expand_query_synonyms_biologic(self):
        expanded = expand_query_synonyms("biologic approval")
        self.assertIn("adalimumab", expanded)
        self.assertIn("high-cost", expanded)
        self.assertTrue(expanded.startswith("biologic approval"))

    def test_expand_query_synonyms_license(self):
        expanded = expand_query_synonyms("doctor license")
        self.assertIn("nmc", expanded)
        self.assertIn("prescriber", expanded)

    def test_expand_query_synonyms_empty_or_whitespace(self):
        self.assertEqual(expand_query_synonyms(""), "")
        self.assertEqual(expand_query_synonyms("   "), "   ")

    def test_retrieve_with_threshold_filtering(self):
        collection_name = "test_threshold_policies"
        seed_policy(
            policy_path=self.policy_path,
            persist_dir=self.persist_dir,
            collection_name=collection_name,
        )

        # Lenient threshold should retrieve chunks
        chunks_lenient = retrieve_policy_chunks(
            query="biologic stamp",
            persist_dir=self.persist_dir,
            collection_name=collection_name,
            threshold=STRICT_THRESHOLD,
        )
        self.assertTrue(len(chunks_lenient) > 0)

        # Impossible/extreme threshold should filter out low similarity
        chunks_strict = retrieve_policy_chunks(
            query="completely unrelated astronomy telescope query",
            persist_dir=self.persist_dir,
            collection_name=collection_name,
            threshold=0.95,
        )
        self.assertEqual(chunks_strict, [])

    def test_synonym_expansion_retrieval(self):
        collection_name = "test_synonym_policies"
        seed_policy(
            policy_path=self.policy_path,
            persist_dir=self.persist_dir,
            collection_name=collection_name,
        )

        # Query using clinical term 'adalimumab' which expands to 'biologic'
        chunks = retrieve_policy_chunks(
            query="adalimumab",
            persist_dir=self.persist_dir,
            collection_name=collection_name,
            expand_synonyms=True,
        )
        self.assertTrue(len(chunks) > 0)
        self.assertTrue(any("Biologics" in c or "biologics" in c.lower() for c in chunks))


if __name__ == "__main__":
    unittest.main()
