"""Guard source decisions, preserve cached evidence, and quarantine bad periods."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from test_reproduction_banks import make_corpus

from reproduction import adjudication, banks


class SourceAdjudicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        make_corpus(self.root)
        records, _ = banks._load_inputs(self.root)
        decisions, tags = [], []
        for record in records:
            identity = {"checkpoint": record.source_checkpoint, "section": "keyword_categories", "row_index": 0}
            decisions.append(
                {
                    **identity,
                    "original_evidence": "Financed renewable energy projects.",
                    "original_amount_eur": 100,
                    "decision": "include",
                    "approved_amount_eur": 50,
                    "amount_adjustment": {"reason": "Explicit employee contribution excluded"},
                    "reason_code": "own_share",
                    "source_report": "reports/example.pdf",
                    "source_pages": [4],
                    "checkpoint_sha256": hashlib.sha256(
                        (self.root / record.source_checkpoint).read_bytes()
                    ).hexdigest(),
                }
            )
            tags.append(
                {
                    **identity,
                    "original_relevant_sdgs": [7, 13],
                    "approved_relevant_sdgs": [7],
                    "rationale": "The claim supports SDG 7.",
                }
            )
        self.decisions = decisions
        (self.root / "reproduction").mkdir()
        self.write("finance_adjudications.json", {"rows": decisions})
        self.write("finance_tag_adjudications.json", {"rows": tags})
        self.write(
            "bank_year_exclusions.json",
            {"rows": [{"country": "finland", "year": 2019, "bank": "Test Bank", "reason": "Wrong source period"}]},
        )

    def write(self, filename, payload):
        (self.root / "reproduction" / filename).write_text(json.dumps(payload))

    def test_replay_changes_only_copies_and_excludes_entire_bad_bank_year(self):
        primary, excluded, audit = adjudication.load(self.root)
        key = self.decisions[0]["checkpoint"]
        row = primary[key]["investments"]["keyword_categories"][0]
        self.assertEqual((row["amount_eur"], row["relevant_sdgs"]), (50, [7]))
        self.assertEqual(
            json.loads((self.root / key).read_text())["investments"]["keyword_categories"][0]["amount_eur"], 100
        )
        result = banks.run(self.root, self.root / "out", primary_overrides=primary, excluded_bank_years=excluded)
        self.assertEqual(result["bank_years"], 11)
        self.assertEqual(result["primary"]["eligible_unique_amount_eur"], 550)
        self.assertEqual(result["corrected_historical_eligible_unique_amount_eur"], 1200)
        self.assertEqual(audit["reviewed_positive_claims"], 12)

    def test_incomplete_review_is_a_hard_error(self):
        self.write("finance_adjudications.json", {"rows": self.decisions[:-1]})
        with self.assertRaisesRegex(ValueError, "cover exactly"):
            adjudication.load(self.root)

    def test_evidence_guard_rejects_stale_decision(self):
        self.decisions[0]["original_evidence"] = "Different claim"
        self.write("finance_adjudications.json", {"rows": self.decisions})
        with self.assertRaisesRegex(ValueError, "evidence/amount guard"):
            adjudication.load(self.root)

    def test_retained_payment_requires_tag_review(self):
        self.write("finance_tag_adjudications.json", {"rows": []})
        with self.assertRaisesRegex(ValueError, "source-reviewed SDG"):
            adjudication.load(self.root)


if __name__ == "__main__":
    unittest.main()
