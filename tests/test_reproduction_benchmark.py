"""Deterministic offline metric, pairing, validation and corpus regression tests."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from reproduction import benchmark


class MetricsTests(unittest.TestCase):
    def test_confusion_and_zero_denominators(self):
        counts = benchmark.confusion([1, 1, 1, 0, 0, 0], [1, 1, 0, 1, 0, 0])
        self.assertEqual(counts, {"tp": 2, "fp": 1, "tn": 2, "fn": 1})
        metrics = benchmark.metrics_from_confusion(counts)
        for name in ("accuracy", "precision", "recall", "f1"):
            self.assertAlmostEqual(metrics[name], 2 / 3)
        self.assertEqual(benchmark.metrics_from_confusion(benchmark.confusion([], []))["f1"], 0)
        self.assertEqual(benchmark.metrics_from_confusion(benchmark.confusion([0], [0]))["accuracy"], 1)
        with self.assertRaises(ValueError):
            benchmark.confusion([1, 0], [1])
        with self.assertRaises(ValueError):
            benchmark.confusion([1, 2], [1, 0])

    def test_average_precision_ties_zero_scores_and_permutation(self):
        # Both score-3 rows enter together: AP=(1/2 + 2/3 + 3/4)/3.
        labels, scores = np.array([1, 0, 1, 1]), np.array([3, 3, 2, 0])
        expected = (1 / 2 + 2 / 3 + 3 / 4) / 3
        self.assertAlmostEqual(benchmark.average_precision(labels, scores), expected)
        self.assertAlmostEqual(benchmark.average_precision(labels[::-1], scores[::-1]), expected)
        self.assertEqual(benchmark.average_precision([0, 0], [2, 0]), 0)
        with self.assertRaises(ValueError):
            benchmark.average_precision([1, 0], [float("nan"), 0])

    def test_cluster_bootstrap_matches_explicit_whole_cluster_expansion(self):
        # Unequal, noncontiguous clusters: independent sampling or averaging
        # cluster F1 would give a different distribution from pooled paired F1.
        texts = ["repeat", "other", "repeat", "third", "repeat"]
        labels = np.array([1, 0, 0, 1, 1], dtype=bool)
        a = np.array([1, 1, 1, 0, 1], dtype=bool)
        b = np.array([0, 0, 1, 1, 0], dtype=bool)
        n, seed = 500, 31
        groups = [[0, 2, 4], [1], [3]]
        rng = np.random.default_rng(seed)
        differences = []
        for _ in range(n):
            indices = [row for group in rng.integers(0, 3, 3) for row in groups[group]]
            y, ap, bp = labels[indices], a[indices], b[indices]

            def f1(y, pred):
                tp = np.sum(y & pred)
                denominator = 2 * tp + np.sum(~y & pred) + np.sum(y & ~pred)
                return 2 * tp / denominator if denominator else 0

            differences.append(f1(y, ap) - f1(y, bp))
        actual = benchmark.paired_bootstrap_f1(labels, a, b, texts=texts, n=n, seed=seed)
        self.assertAlmostEqual(actual["mean_diff"], np.mean(differences))
        self.assertAlmostEqual(actual["ci95_low"], np.quantile(differences, 0.025))
        self.assertAlmostEqual(actual["ci95_high"], np.quantile(differences, 0.975))
        self.assertEqual(actual["p_diff_le_0"], np.mean(np.array(differences) <= 0))
        identical = benchmark.paired_bootstrap_f1(labels, a, a, texts=texts, n=n, seed=seed)
        self.assertEqual(identical, {"mean_diff": 0, "ci95_low": 0, "ci95_high": 0, "p_diff_le_0": 1})

    def test_exact_text_equality_and_single_cluster(self):
        # Whitespace, case and Unicode normalization remain distinct clusters.
        texts = ["x", "x ", "X", "é", "e\u0301"]
        y, a, b = [1, 0, 1, 1, 0], [1, 0, 0, 1, 1], [0, 1, 1, 1, 0]
        row = benchmark.paired_bootstrap_f1(y, a, b, n=100)
        cluster = benchmark.paired_bootstrap_f1(y, a, b, texts=texts, n=100)
        self.assertEqual(row, cluster)
        single = benchmark.paired_bootstrap_f1(y, a, b, texts=["same"] * 5, n=100)
        observed = (
            benchmark.metrics_from_confusion(benchmark.confusion(y, a))["f1"]
            - benchmark.metrics_from_confusion(benchmark.confusion(y, b))["f1"]
        )
        self.assertAlmostEqual(single["ci95_low"], observed)
        self.assertAlmostEqual(single["ci95_high"], observed)
        for kwargs in ({"texts": ["x"]}, {"n": 0}, {"texts": [None] * 5}):
            with self.assertRaises(ValueError):
                benchmark.paired_bootstrap_f1(y, a, b, **kwargs)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / benchmark.BENCHMARK_DIR
        self.directory.mkdir(parents=True)
        self.rows = [
            {"id": "a", "text": "same text", "sdg": 1, "label": True},
            {"id": "b", "text": "same text", "sdg": 2, "label": False},
            {"id": "c", "text": "different", "sdg": 3, "label": True},
        ]
        self.scores = {"a": {1: 3.0}, "b": {1: 2.5}, "c": {3: 2.5}}
        self.baseline = [
            {
                "id": row["id"],
                "text": row["text"],
                "sdg": row["sdg"],
                "expected_label": row["label"],
                "predictions": "[1]",
                "predicted_label": row["sdg"] == 1,
                "is_correct": (row["sdg"] == 1) == row["label"],
            }
            for row in self.rows
        ]
        self.results = [
            {
                **row,
                "jrc_pred": row["sdg"] == 1,
                "gpt_target_score": self.scores[row["id"]].get(row["sdg"], 0),
                "gpt_scores": str(self.scores[row["id"]]),
                **{f"gpt_pred_ge_{t}": self.scores[row["id"]].get(row["sdg"], 0) >= t for t in range(1, 6)},
            }
            for row in self.rows
        ]
        self.cache = [
            {"id": row["id"], "run_config_hash": "a" * 64, "sdg_scores": self.scores[row["id"]]} for row in self.rows
        ]
        self.saved = {"framing": "generic", "model": "openai/gpt-oss-120b", "run_config_hash": "a" * 64}
        self.write_csv("benchmark", self.rows)
        self.write_csv("baseline", self.baseline)
        self.write_csv("results", self.results)
        self.write_cache()
        self.path("metrics").write_text(json.dumps(self.saved), encoding="utf-8")

    def path(self, name):
        return self.directory / benchmark.INPUT_NAMES[name]

    def write_csv(self, name, rows):
        with self.path(name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def write_cache(self):
        self.path("predictions").write_text("\n".join(json.dumps(row) for row in self.cache) + "\n", encoding="utf-8")

    def load(self):
        return benchmark._load_inputs(self.root)

    def test_reordered_joins_preserve_benchmark_order(self):
        self.write_csv("baseline", self.baseline[::-1])
        self.write_csv("results", self.results[::-1])
        joined, _, _ = self.load()
        self.assertEqual([row["id"] for row in joined], ["a", "b", "c"])
        self.assertEqual([row["score"] for row in joined], [3, 0, 2.5])

    def test_missing_input_names_are_actionable(self):
        self.path("baseline").unlink()
        self.path("predictions").unlink()
        with self.assertRaises(FileNotFoundError) as exc:
            benchmark.run(self.root, self.root / "out")
        self.assertIn(benchmark.INPUT_NAMES["baseline"], str(exc.exception))
        self.assertIn(benchmark.INPUT_NAMES["predictions"], str(exc.exception))
        self.assertFalse((self.root / "out").exists())

    def test_duplicate_missing_and_extra_row_keys(self):
        for rows in (
            self.results + [self.results[0]],
            self.results[:2],
            self.results + [{**self.results[0], "id": "extra"}],
        ):
            with self.subTest(rows=len(rows)):
                self.write_csv("results", rows)
                with self.assertRaisesRegex(ValueError, "duplicate|coverage mismatch"):
                    self.load()

    def test_label_text_score_and_boolean_corruption(self):
        cases = [
            ("label", False),
            ("label", "yes"),
            ("text", "same text "),
            ("gpt_target_score", 2.9),
            ("gpt_target_score", "nan"),
            ("gpt_scores", "{1: 2.0}"),
            ("gpt_pred_ge_3", False),
            ("jrc_pred", False),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                self.write_csv("results", [{**self.results[0], field: value}, *self.results[1:]])
                with self.assertRaises(ValueError):
                    self.load()

    def test_baseline_list_and_correctness_are_validated(self):
        for change in ({"predictions": "[]"}, {"is_correct": False}, {"expected_label": False}):
            with self.subTest(change=change):
                self.write_csv("baseline", [{**self.baseline[0], **change}, *self.baseline[1:]])
                with self.assertRaises(ValueError):
                    self.load()

    def test_cache_hash_coverage_duplicates_and_score_range(self):
        original = self.cache
        cases = [original[:2], original + [original[0]], [{**original[0], "run_config_hash": "b" * 64}, *original[1:]]]
        cases.extend(
            [{**original[0], "sdg_scores": {"1": score}}, *original[1:]]
            for score in (float("nan"), float("inf"), -1, 0, 6, True)
        )
        for cache in cases:
            with self.subTest(cache=cache[0]):
                self.cache = cache
                self.write_cache()
                with self.assertRaises(ValueError):
                    self.load()

    def test_missing_columns_empty_and_duplicate_json_keys(self):
        original = self.path("benchmark").read_text(encoding="utf-8")
        for bad in ("id,text,sdg\na,text,1\n", "id,text,sdg,label\n"):
            self.path("benchmark").write_text(bad, encoding="utf-8")
            with self.assertRaises(ValueError):
                self.load()
        self.path("benchmark").write_text(original, encoding="utf-8")
        self.path("predictions").write_text('{"id":"a","id":"b"}\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            self.load()

    def test_metric_mismatch_is_reported_without_editing_input(self):
        before = {name: self.path(name).read_bytes() for name in benchmark.INPUT_NAMES}
        # Exercise real serialization/bootstrap even on a small fixture; no API
        # modules are imported, and accidental socket use immediately fails.
        with patch("socket.socket", side_effect=AssertionError("network forbidden")):
            report = benchmark.run(self.root, self.root / "nested" / "output")
        self.assertEqual(report["status"], "mismatch")
        self.assertEqual(report["counts"]["unique_texts"], 2)
        self.assertEqual(report["missed_positives"]["below_threshold"]["3"], 1)
        self.assertEqual(report["rounded_centrality_precision_historical"]["2"]["n"], 1)
        self.assertEqual(report["provenance"]["source_config"]["status"], "unavailable")
        self.assertIn("n_rows", [item["field"] for item in report["validation"]["mismatches"]])
        output = self.root / "nested" / "output"
        self.assertEqual(json.loads((output / "benchmark_summary.json").read_text()), report)
        self.assertEqual({name: self.path(name).read_bytes() for name in benchmark.INPUT_NAMES}, before)
        for filename in report["artifacts"].values():
            self.assertTrue((output / filename).is_file())
        mismatch = benchmark._metric_mismatches({"f1": 0.8}, {"f1": 0.7})
        self.assertEqual(mismatch, [{"field": "f1", "recomputed": 0.8, "saved": 0.7}])

    def test_source_metadata_is_parsed_without_executing_code(self):
        source_dir = self.root / "honesty_scorer"
        source_dir.mkdir()
        (source_dir / "constants.py").write_text(
            "raise RuntimeError('source must never execute')\n"
            "DEFAULT_OPENROUTER_MODEL = 'openai/gpt-oss-120b'\n"
            "SDG_MENTIONS_SYSTEM_PROMPT_GENERIC = 'system'\n"
            "SDG_MENTIONS_USER_TEMPLATE_GENERIC = 'user {report_text}'\n",
            encoding="utf-8",
        )
        _, saved, paths = self.load()
        first = benchmark._provenance(self.root, paths, saved)
        self.assertEqual(first["source_config"]["status"], "mismatch")
        saved["run_config_hash"] = first["source_config"]["reconstructed_run_config_hash"]
        self.assertEqual(benchmark._provenance(self.root, paths, saved)["source_config"]["status"], "matched")
        saved["model"] = "different-declared-model"
        self.assertEqual(benchmark._provenance(self.root, paths, saved)["source_config"]["status"], "mismatch")

    def test_output_alias_cannot_overwrite_input(self):
        output = self.root / "out"
        output.mkdir()
        before = self.path("benchmark").read_bytes()
        (output / "benchmark_thresholds.csv").symlink_to(self.path("benchmark"))
        with self.assertRaisesRegex(ValueError, "aliases an input"):
            benchmark.run(self.root, output)
        self.assertEqual(self.path("benchmark").read_bytes(), before)
        self.assertFalse((output / "benchmark_summary.json").exists())


class CorpusRegressionTests(unittest.TestCase):
    def test_full_cached_study_and_historical_row_bootstrap(self):
        root = Path(__file__).resolve().parents[1]
        if not (root / benchmark.BENCHMARK_DIR / benchmark.INPUT_NAMES["metrics"]).is_file():
            self.skipTest("full study inputs not installed; fixture validation tests still run")
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("socket.socket", side_effect=AssertionError("network forbidden")),
        ):
            report = benchmark.run(root, Path(directory))
        self.assertEqual(report["validation"]["mismatches"], [])
        self.assertEqual(report["counts"]["rows"], 1251)
        self.assertEqual(report["counts"]["unique_texts"], 1247)
        self.assertEqual(report["missed_positives"]["target_score_zero"], 52)
        self.assertEqual(report["missed_positives"]["below_threshold"]["3"], 106)
        self.assertAlmostEqual(report["primary"]["gpt_micro"]["f1"], 0.8471760797342193, places=14)
        self.assertAlmostEqual(report["primary"]["jrc_micro"]["f1"], 0.7209533267130089, places=14)
        self.assertAlmostEqual(report["primary"]["row_bootstrap"]["ci95_low"], 0.09141360476899163, places=14)
        self.assertAlmostEqual(report["primary"]["row_bootstrap"]["ci95_high"], 0.1616734815778963, places=14)
        self.assertAlmostEqual(report["primary"]["cluster_bootstrap"]["ci95_low"], 0.09210865387531286, places=14)
        self.assertAlmostEqual(report["primary"]["cluster_bootstrap"]["ci95_high"], 0.16192335619668907, places=14)
        self.assertEqual(len(report["provenance"]["files"]["benchmark"]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
