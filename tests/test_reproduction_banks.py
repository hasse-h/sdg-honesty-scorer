"""Offline contract and numerical tests for the cached bank reproduction."""

import copy
import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from reproduction import banks


def investment(amount=100, sdgs=None, **overrides):
    return {
        "amount_eur": amount,
        "relevant_sdgs": [7, 13] if sdgs is None else sdgs,
        "construct_type": "disclosed_sdg_linked_finance",
        "score_eligible": True,
        "inclusion_policy": "linked_scored",
        "evidence": "Financed renewable energy projects.",
        "page_numbers": [4],
        "exclusion_reason": "",
        **overrides,
    }


def checkpoint(mentions=(), rows=(), bank="Finland_Test Bank_2019"):
    return {
        "bank": bank,
        "mentions": {
            "sdg_data": [
                {"sdg_number": sdg, "mention_count": count, "importance_score": importance, "page_numbers": [1]}
                for sdg, count, importance in mentions
            ]
        },
        "investments": {"keyword_categories": list(rows), "investment_instruments": []},
    }


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_corpus(root):
    """Twelve complete country-years; independent hand-calculated references."""
    totals, profiles, pooled = [], [], []
    for country in banks.COUNTRIES:
        for year in banks.YEARS:
            stem = f"{country}_{year}"
            write_csv(
                root / banks.MANIFEST_PATH / f"bank_reports_{stem}.csv",
                [
                    {
                        "path": f"../reports/{stem}.pdf",
                        "bank": "Test Bank",
                        "country": country.title(),
                        "year": year,
                        "report_type": "annual_report",
                    }
                ],
            )
            for subdir, amount in (("checkpoints", 200), ("checkpoints_corrected", 100)):
                path = root / banks.RUN_PATH / stem / subdir / "bank.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                data = checkpoint(
                    [(7, 2, 5), (13, 5, 1)], [investment(amount)], bank=f"{country.title()}_Test Bank_{year}"
                )
                path.write_text(json.dumps(data), encoding="utf-8")
            totals.append(
                {
                    "stem": stem,
                    **{
                        phase: {"linked_total": amount, "score_eligible_rows": 1, "finance_rows": 1, "banks": 1}
                        for phase, amount in (("before", 200), ("after", 100))
                    },
                }
            )
            for sdg in banks.SDGS:
                profiles.append(
                    {
                        "country": country,
                        "year": year,
                        "sdg": sdg,
                        "narrative_weight": 10 if sdg == 7 else 0,
                        "finance_eur": 100 if sdg in (7, 13) else 0,
                        "narrative_share": 1 if sdg == 7 else 0,
                        "finance_share": 0.5 if sdg in (7, 13) else 0,
                        "gap_pp": 50 if sdg == 7 else -50 if sdg == 13 else 0,
                    }
                )
        for sdg in banks.SDGS:
            pooled.append(
                {
                    "country": country,
                    "sdg": sdg,
                    "narrative_weight": 60 if sdg == 7 else 0,
                    "finance_eur": 600 if sdg in (7, 13) else 0,
                    "narrative_share": 1 if sdg == 7 else 0,
                    "finance_share": 0.5 if sdg in (7, 13) else 0,
                    "gap_pp": 50 if sdg == 7 else -50 if sdg == 13 else 0,
                }
            )
    path = root / banks.TOTALS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(totals), encoding="utf-8")
    write_csv(root / banks.PROFILE_PATH / "sdg_profiles_by_country_year.csv", profiles)
    write_csv(root / banks.PROFILE_PATH / "sdg_profiles_pooled_2019_2024.csv", pooled)


class BankScoringTests(unittest.TestCase):
    def test_full_and_fractional_use_distinct_tags_and_conserve_only_fractional(self):
        data = checkpoint([(7, 1, 5)], [investment(120, [7, 7, 13]), investment(60, [7])])
        full, full_sdgs = banks._analyze(data)
        fractional, fractional_sdgs = banks._analyze(data, fractional=True)
        f = {r["sdg"]: r for r in full_sdgs}
        a = {r["sdg"]: r for r in fractional_sdgs}
        self.assertEqual(full["eligible_unique_amount_eur"], 180)
        self.assertEqual(full["tagged_exposure_total_eur"], 300)
        self.assertEqual((f[7]["A_eur"], f[13]["A_eur"]), (180, 120))
        self.assertEqual(f[7]["E"], 3)
        self.assertEqual(full["M"], 4)
        self.assertEqual(fractional["tagged_exposure_total_eur"], 180)
        self.assertEqual((a[7]["A_eur"], a[13]["A_eur"]), (120, 60))
        self.assertAlmostEqual(fractional["M"], 10 / 3)

    def test_both_zero_silence_and_one_sided_zero(self):
        silent, _ = banks._analyze(checkpoint([(7, 8, 2)]))
        self.assertTrue(silent["silent"])
        self.assertEqual(silent["AS"], 1)
        self.assertIsNone(silent["normalized_alignment"])
        finance_only, _ = banks._analyze(checkpoint(rows=[investment(10, [7])]))
        narrative_only, _ = banks._analyze(checkpoint([(7, 1, 5)]))
        for metrics in (finance_only, narrative_only):
            self.assertFalse(metrics["silent"])
            self.assertEqual(metrics["M"], 5)
            self.assertEqual(metrics["normalized_alignment"], 0.5)
        aggregate = banks._aggregate([silent, finance_only])
        self.assertEqual(aggregate["silent_banks"], 1)
        self.assertEqual(aggregate["mean_AS_non_silent"], finance_only["AS"])
        self.assertGreater(aggregate["mean_AS_all"], aggregate["mean_AS_non_silent"])

    def test_strict_undrawn_ignores_financing_verb_but_preserves_other_classifications(self):
        data = checkpoint(
            rows=[
                investment(
                    75, construct_type="credit_limit_undrawn", evidence="Agreements were financed; credit limits."
                ),
                investment(50, evidence="Agreements were financed; credit limits."),
                investment(900, score_eligible=False),
                investment(800, inclusion_policy="gross_context_only"),
            ]
        )
        original = copy.deepcopy(data)
        strict, _ = banks._analyze(data)
        legacy, _ = banks._analyze(data, strict=False)
        self.assertEqual(strict["eligible_unique_amount_eur"], 50)
        self.assertEqual(legacy["eligible_unique_amount_eur"], 125)
        self.assertEqual(data, original)
        record = banks.BankYear(
            "finland", 2019, "Test Bank", "corrected.json", "raw.json", "manifest.csv", [], data, data
        )
        audit = banks._audit(record)
        self.assertTrue(audit[0]["impacted_by_strict_undrawn_exclusion"])
        self.assertIn("strict_primary_excludes_credit_limit_undrawn", audit[0]["primary_exclusion_reason"])
        self.assertTrue(audit[1]["primary_eligible"])
        self.assertTrue(audit[1]["credit_limit_evidence_requires_separate_adjudication"])
        self.assertEqual(audit[0]["source_checkpoint"], "corrected.json")
        self.assertEqual(audit[0]["page_numbers"], [4])

    def test_count_weighted_composition_is_not_score_centrality(self):
        data = checkpoint([(7, 100, 5), (13, 1, 5)], [investment()])
        metrics, sdgs = banks._analyze(data)
        self.assertEqual(metrics["M"], 5)
        self.assertEqual(metrics["normalized_alignment"], 1)
        self.assertNotEqual(metrics["AS"], metrics["normalized_alignment"])
        profile = banks._profiles(
            [{**r, "country": "finland", "year": 2020} for r in sdgs], [{**metrics, "country": "finland", "year": 2020}]
        )
        by_sdg = {r["sdg"]: r for r in profile}
        self.assertAlmostEqual(by_sdg[7]["narrative_share"], 100 / 101)
        self.assertEqual(by_sdg[7]["finance_eur"], 100)
        self.assertEqual(sum(r["finance_eur"] for r in profile), 200)
        self.assertEqual(sum(r["normalized_allocated_eur_for_display"] for r in profile), 100)
        self.assertEqual(by_sdg[7]["finance_eur_basis"], "tagged_exposure_not_conserved_money")

    def test_max_centrality_and_threshold_sensitivities(self):
        data = checkpoint([(7, 2, 2), (7, 3, 4), (13, 5, 2), (17, 7, 1)])
        main, sdgs = banks._analyze(data)
        threshold2, _ = banks._analyze(data, threshold=2)
        threshold1, _ = banks._analyze(data, threshold=1)
        self.assertEqual((main["retained_mentions"], main["M"]), (5, 4))
        self.assertEqual((threshold2["retained_mentions"], threshold2["M"]), (10, 6))
        self.assertEqual((threshold1["retained_mentions"], threshold1["M"]), (17, 7))
        self.assertEqual(next(r for r in sdgs if r["sdg"] == 7)["R"], 4)

    def test_pearson_and_undefined_cases(self):
        rows = [{"AS": x, "retained_mentions": y, "silent": False} for x, y in ((0.1, 30), (0.2, 20), (0.3, 10))]
        self.assertAlmostEqual(banks._pearson(rows), -1)
        self.assertIsNone(banks._pearson(rows[:1]))
        self.assertIsNone(banks._pearson([{**r, "retained_mentions": 5} for r in rows]))
        self.assertAlmostEqual(banks._pearson([*rows, {"AS": 1, "retained_mentions": 0, "silent": True}]), -1)

    def test_aggregate_uses_unrounded_scores(self):
        metrics, _ = banks._analyze(checkpoint([(7, 1, 3)], [investment(100, [7]), investment(3, [13])]))
        self.assertNotEqual(metrics["AS"], round(metrics["AS"], 4))
        self.assertEqual(banks._aggregate([metrics])["mean_AS_all"], metrics["AS"])
        display = banks._display(metrics)
        self.assertEqual(display["AS"], round(1 - round(metrics["M"], 4) / 85, 4))

    def test_complete_panels_keep_exact_predecessor_identities(self):
        records, rows = [], []
        for bank, years in (
            ("Stable", banks.YEARS),
            ("Alisa Pankki", (2022, 2023, 2024)),
            ("Evli Pankki", (2019, 2020, 2021)),
        ):
            for year in years:
                data = checkpoint([] if year == 2020 else [(7, 1, 5)])
                record = banks.BankYear("finland", year, bank, "c.json", "r.json", "m.csv", [], data, data)
                records.append(record)
                rows.append({**record.identity(), **banks._analyze(data)[0]})
        coverage = banks._coverage(records, rows)
        observations, summaries = banks._panels(rows, coverage)
        self.assertEqual({r["bank"] for r in observations}, {"Stable"})
        self.assertEqual(sum(r["panel"] == "complete_including_both_zero" for r in observations), 6)
        self.assertEqual(sum(r["panel"] == "complete_excluding_both_zero_observations" for r in observations), 5)
        self.assertFalse(any(r["panel"] == "complete_never_both_zero_banks" for r in observations))
        dropped = next(
            r
            for r in summaries
            if r["country"] == "finland"
            and r["year"] == 2020
            and r["panel"] == "complete_excluding_both_zero_observations"
        )
        self.assertEqual(dropped["enrolled_complete_banks"], 1)
        self.assertEqual(dropped["banks"], 0)
        self.assertFalse(dropped["balanced_panel_guaranteed"])


class BankReproductionInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "portable repo with spaces"
        self.output = Path(self.temp.name) / "outputs"
        make_corpus(self.root)

    def test_full_run_is_offline_deterministic_and_preserves_inputs(self):
        inputs = sorted(p for p in self.root.rglob("*") if p.is_file())
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
        with patch("socket.socket", side_effect=AssertionError("Network forbidden")):
            result = banks.run(self.root, self.output)
        self.assertTrue(result["validation_passed"])
        self.assertEqual(result["primary"]["eligible_unique_amount_eur"], 1200)
        self.assertEqual(result["bank_years"], 12)
        self.assertAlmostEqual(result["primary"]["mean_AS_all"], 16 / 17)
        self.assertEqual(set(result["artifacts"]), {p.name for p in self.output.iterdir()})
        first = {p.name: p.read_bytes() for p in self.output.iterdir()}
        self.assertEqual(banks.run(self.root, self.output), result)
        self.assertEqual(first, {p.name: p.read_bytes() for p in self.output.iterdir()})
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
        self.assertEqual(json.loads((self.output / "summary.json").read_text()), result)
        sensitivity = banks._read_csv(self.output / "sensitivity_bank_year.csv")
        normalized = [r for r in sensitivity if r["variant"] == "symmetric_normalized_alignment"]
        self.assertTrue(all(r["AS"] == "" and r["normalized_alignment"] == "0.5" for r in normalized))
        self.assertEqual(len(banks._read_csv(self.output / "bank_sdg.csv")), 12 * 17)
        country = banks._read_csv(self.output / "country_year.csv")[0]
        self.assertEqual(float(country["historical_raw_eligible_unique_amount_eur"]), 200)
        self.assertEqual(float(country["corrected_historical_eligible_unique_amount_eur"]), 100)
        self.assertEqual(country["source_file_count"], "1")

    def test_missing_manifest_is_a_hard_error(self):
        (self.root / banks.MANIFEST_PATH / "bank_reports_finland_2019.csv").unlink()
        with self.assertRaises(FileNotFoundError):
            banks.run(self.root, self.output)

    def test_strict_policy_change_keeps_historical_reference_validation_separate(self):
        path = self.root / banks.RUN_PATH / "finland_2019/checkpoints_corrected/bank.json"
        data = json.loads(path.read_text())
        data["investments"]["keyword_categories"][0]["construct_type"] = "credit_limit_undrawn"
        path.write_text(json.dumps(data))
        result = banks.run(self.root, self.output)
        self.assertTrue(result["validation_passed"])
        self.assertEqual(result["corrected_historical_eligible_unique_amount_eur"], 1200)
        self.assertEqual(result["primary"]["eligible_unique_amount_eur"], 1100)
        self.assertEqual(result["strict_undrawn_impacted_rows"], 1)
        self.assertEqual(result["strict_undrawn_removed_unique_eur"], 100)
        impacted = banks._read_csv(self.output / "undrawn_impacted_rows.csv")
        self.assertEqual(len(impacted), 1)
        self.assertEqual(impacted[0]["original_score_eligible"], "True")
        self.assertEqual(impacted[0]["primary_eligible"], "False")
        primary = banks._read_csv(self.output / "country_year_sdg_profiles.csv")
        historical = banks._read_csv(self.output / "historical_country_year_sdg_profiles.csv")

        def select(rows):
            return next(r for r in rows if r["country"] == "finland" and r["year"] == "2019" and r["sdg"] == "7")

        self.assertEqual(float(select(primary)["finance_eur"]), 0)
        self.assertEqual(float(select(historical)["finance_eur"]), 100)

    def test_missing_raw_or_corrected_checkpoint_is_a_hard_error(self):
        for subdir in ("checkpoints", "checkpoints_corrected"):
            with self.subTest(subdir=subdir):
                path = self.root / banks.RUN_PATH / "finland_2019" / subdir / "bank.json"
                original = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(FileNotFoundError, "Missing checkpoints"):
                    banks.run(self.root, self.output)
                path.write_bytes(original)

    def test_partial_bank_coverage_is_a_hard_error(self):
        path = self.root / banks.MANIFEST_PATH / "bank_reports_finland_2019.csv"
        rows = banks._read_csv(path)
        write_csv(path, [*rows, {**rows[0], "bank": "Missing Bank", "path": "missing.pdf"}])
        with self.assertRaisesRegex(FileNotFoundError, "Missing bank-year checkpoints"):
            banks.run(self.root, self.output)

    def test_duplicate_bankyear_is_a_hard_error(self):
        path = self.root / banks.RUN_PATH / "finland_2019/checkpoints_corrected/bank.json"
        path.with_name("duplicate.json").write_bytes(path.read_bytes())
        with self.assertRaisesRegex(ValueError, "Duplicate bank-year"):
            banks.run(self.root, self.output)

    def test_manifest_identity_does_not_fall_back_to_filename(self):
        path = self.root / banks.RUN_PATH / "finland_2019/checkpoints_corrected/bank.json"
        data = json.loads(path.read_text())
        data["bank"] = "Finland_Another Bank_2019"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "exact manifest identities"):
            banks.run(self.root, self.output)

    def test_historical_totals_validation_detects_changed_amount(self):
        path = self.root / banks.RUN_PATH / "finland_2019/checkpoints_corrected/bank.json"
        data = json.loads(path.read_text())
        data["investments"]["keyword_categories"][0]["amount_eur"] += 1
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "Historical totals mismatch"):
            banks.run(self.root, self.output)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_figure5_validation_detects_wrong_profile(self):
        path = self.root / banks.PROFILE_PATH / "sdg_profiles_by_country_year.csv"
        rows = banks._read_csv(path)
        rows[0]["gap_pp"] = "0.2"
        write_csv(path, rows)
        with self.assertRaisesRegex(ValueError, "Historical Figure 5 profile mismatch"):
            banks.run(self.root, self.output)

    def test_missing_validation_source_is_a_hard_error(self):
        (self.root / banks.TOTALS_PATH).unlink()
        with self.assertRaises(FileNotFoundError):
            banks.run(self.root, self.output)

    def test_output_cannot_overwrite_canonical_inputs(self):
        with self.assertRaisesRegex(ValueError, "historical input"):
            banks.run(self.root, self.root / banks.RUN_PATH)

    def test_output_artifact_alias_cannot_mutate_historical_input(self):
        import os

        self.output.mkdir()
        source = self.root / banks.RUN_PATH / "finland_2019/checkpoints_corrected/bank.json"
        original = source.read_bytes()
        target = self.output / "bank_year.csv"
        for link in (os.symlink, os.link):
            with self.subTest(link=link.__name__):
                link(source, target)
                with self.assertRaisesRegex(ValueError, "symlink|aliases a historical input"):
                    banks.run(self.root, self.output)
                self.assertEqual(source.read_bytes(), original)
                self.assertEqual(list(self.output.iterdir()), [target])
                target.unlink()


if __name__ == "__main__":
    unittest.main()
