"""Offline reproduction of the fixed generic SDG benchmark prediction cache.

Only local CSV/JSON/source files are read; the original API-enabled harness is
never imported. ``run`` writes new, compact artifacts without editing its inputs.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import math
import platform
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

BENCHMARK_DIR = Path("evaluations/sdg_benchmark")
INPUT_NAMES = {
    "benchmark": "benchmark.csv",
    "baseline": "sdg_mapper_results.csv",
    "results": "gpt_oss_120b_generic_results.csv",
    "predictions": "gpt_oss_120b_generic_predictions.jsonl",
    "metrics": "gpt_oss_120b_vs_jrc_generic_metrics.json",
}
BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 20260504
TEXT_EQUALITY = (
    "Exact equality of decoded UTF-8 CSV text field strings, including case, whitespace, "
    "embedded line endings and Unicode code points; no stripping, case folding, Unicode "
    "normalization, hashing-based grouping or deduplication. Clusters are ordered by first "
    "appearance in benchmark.csv, regardless of row ID or SDG."
)


def _binary(values: Any, name: str) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 1 or not np.all(np.isin(array, [False, True])):
        raise ValueError(f"{name} must be a one-dimensional binary array")
    return array.astype(bool)


def confusion(y_true: Any, y_pred: Any) -> dict[str, int]:
    """Binary row-level confusion counts; reject non-binary or unpaired arrays."""
    y, pred = _binary(y_true, "labels"), _binary(y_pred, "predictions")
    if y.shape != pred.shape:
        raise ValueError("labels and predictions must have the same shape")
    return {
        "tp": int(np.sum(y & pred)),
        "fp": int(np.sum(~y & pred)),
        "tn": int(np.sum(~y & ~pred)),
        "fn": int(np.sum(y & ~pred)),
    }


def metrics_from_confusion(c: dict[str, int]) -> dict[str, Any]:
    """Match the historical precision/recall/F1 operation order and zero policy."""
    tp, fp, tn, fn = (int(c[key]) for key in ("tp", "fp", "tn", "fn"))
    if any(c[key] != int(c[key]) or c[key] < 0 for key in ("tp", "fp", "tn", "fn")):
        raise ValueError("confusion counts must be nonnegative integers")
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    total = tp + fp + tn + fn
    return {
        "accuracy": (tp + tn) / total if total else 0.0,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def average_precision(y_true: Any, scores: Any) -> float:
    """Non-interpolated AP, grouping all tied scores before computing precision."""
    y = _binary(y_true, "labels")
    scores = np.asarray(scores, dtype=float)
    if y.shape != scores.shape or not np.all(np.isfinite(scores)):
        raise ValueError("scores must be finite and aligned with labels")
    if not np.any(y):
        return 0.0
    precisions = []
    for score in sorted(set(scores), reverse=True):
        selected = scores >= score
        precisions.extend([float(np.mean(y[selected]))] * int(np.sum(y & (scores == score))))
    return float(np.sum(precisions) / np.sum(y))


def _f1(y: np.ndarray, pred: np.ndarray) -> float:
    # Internal arrays are already validated; retain the historical arithmetic.
    return metrics_from_confusion(
        {
            "tp": int(np.sum(y & pred)),
            "fp": int(np.sum(~y & pred)),
            "tn": int(np.sum(~y & ~pred)),
            "fn": int(np.sum(y & ~pred)),
        }
    )["f1"]


def paired_bootstrap_f1(
    y_true: Any,
    a_pred: Any,
    b_pred: Any,
    *,
    texts: list[str] | None = None,
    n: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, float]:
    """Paired row bootstrap, or paired whole-text cluster bootstrap.

    Each draw samples N rows or K text clusters with replacement. Cluster
    multiplicity weights all constituent rows equally for both models. Micro
    F1 is computed from pooled counts, never averaged across clusters.
    """
    y, a, b = (
        _binary(values, name)
        for values, name in ((y_true, "labels"), (a_pred, "a predictions"), (b_pred, "b predictions"))
    )
    if not len(y) or y.shape != a.shape or y.shape != b.shape:
        raise ValueError("bootstrap needs nonempty, equally sized paired arrays")
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise ValueError("bootstrap draw count must be a positive integer")
    rng = np.random.default_rng(seed)
    diffs = np.empty(n)
    if texts is None:
        for index in range(n):
            sample = rng.integers(0, len(y), len(y))
            diffs[index] = _f1(y[sample], a[sample]) - _f1(y[sample], b[sample])
    else:
        if len(texts) != len(y) or any(not isinstance(text, str) or not text for text in texts):
            raise ValueError("texts must be nonempty strings aligned with the paired arrays")
        groups: dict[str, int] = {}
        codes = np.array([groups.setdefault(text, len(groups)) for text in texts])
        counts = np.zeros((len(groups), 8), dtype=np.int64)
        row_counts = np.column_stack((y & a, ~y & a, ~y & ~a, y & ~a, y & b, ~y & b, ~y & ~b, y & ~b))
        np.add.at(counts, codes, row_counts)
        for index in range(n):
            sample = rng.integers(0, len(groups), len(groups))
            totals = counts[sample].sum(axis=0)
            f1_a = metrics_from_confusion(dict(zip(("tp", "fp", "tn", "fn"), totals[:4])))["f1"]
            f1_b = metrics_from_confusion(dict(zip(("tp", "fp", "tn", "fn"), totals[4:])))["f1"]
            diffs[index] = f1_a - f1_b
    return {
        "mean_diff": float(np.mean(diffs)),
        "ci95_low": float(np.quantile(diffs, 0.025)),
        "ci95_high": float(np.quantile(diffs, 0.975)),
        "p_diff_le_0": float(np.mean(diffs <= 0)),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bool(value: str, location: str) -> bool:
    if value not in ("True", "False"):
        raise ValueError(f"{location}: expected literal True or False, got {value!r}")
    return value == "True"


def _sdg(value: Any, location: str) -> int:
    if isinstance(value, bool) or str(value) not in {str(n) for n in range(1, 18)}:
        raise ValueError(f"{location}: invalid SDG {value!r}")
    return int(value)


def _scores(value: Any, location: str) -> dict[int, float]:
    if not isinstance(value, dict):
        raise ValueError(f"{location}: scores must be an object")
    result = {}
    for key, score in value.items():
        sdg = _sdg(key, location)
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(score)
            or not 0 < score <= 5
            or sdg in result
        ):
            raise ValueError(f"{location}: invalid or duplicate cached score for SDG {sdg}")
        result[sdg] = float(score)
    return result


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not required.issubset(fields):
            raise ValueError(f"{path.name}: missing columns or duplicate header; required {sorted(required)}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path.name}: empty input")
    for number, row in enumerate(rows, 2):
        if None in row or any(row[field] is None for field in fields):
            raise ValueError(f"{path.name} row {number}: malformed CSV row")
        if not row["id"].strip() or not row["text"].strip():
            raise ValueError(f"{path.name} row {number}: empty id or text")
    return rows


def _index(rows: list[dict[str, str]], name: str) -> dict[tuple[str, int], dict[str, str]]:
    indexed = {}
    id_text = {}
    for row in rows:
        key = (row["id"], _sdg(row["sdg"], name))
        if key in indexed:
            raise ValueError(f"{name}: duplicate (id, sdg) key {key}")
        if id_text.setdefault(row["id"], row["text"]) != row["text"]:
            raise ValueError(f"{name}: one id maps to multiple texts: {row['id']}")
        indexed[key] = row
    return indexed


def _load_inputs(repo_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Path]]:
    paths = {key: repo_root / BENCHMARK_DIR / name for key, name in INPUT_NAMES.items()}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing offline benchmark inputs: " + ", ".join(missing))
    saved = json.loads(paths["metrics"].read_text(encoding="utf-8"), object_pairs_hook=_json_object)
    if not isinstance(saved, dict) or saved.get("framing") != "generic":
        raise ValueError("saved metrics must describe generic framing")
    config_hash = saved.get("run_config_hash")
    if (
        not isinstance(config_hash, str)
        or len(config_hash) != 64
        or any(c not in "0123456789abcdef" for c in config_hash)
    ):
        raise ValueError("saved metrics have an invalid run_config_hash")
    if not isinstance(saved.get("model"), str) or not saved["model"]:
        raise ValueError("saved metrics lack model metadata")
    if saved.get("sample_size") is not None or saved.get("sample_seed") is not None:
        raise ValueError("saved metrics must describe the full benchmark, not a sampled run")
    base_columns = {"id", "text", "sdg"}
    benchmark = _index(_read_csv(paths["benchmark"], base_columns | {"label"}), "benchmark")
    baseline = _index(
        _read_csv(paths["baseline"], base_columns | {"expected_label", "predictions", "predicted_label", "is_correct"}),
        "baseline",
    )
    results = _index(
        _read_csv(
            paths["results"],
            base_columns
            | {"label", "jrc_pred", "gpt_target_score", "gpt_scores", *(f"gpt_pred_ge_{t}" for t in range(1, 6))},
        ),
        "results",
    )
    for name, indexed in (("baseline", baseline), ("results", results)):
        if indexed.keys() != benchmark.keys():
            raise ValueError(
                f"{name}: row key coverage mismatch against benchmark "
                f"(missing={len(benchmark.keys() - indexed.keys())}, "
                f"extra={len(indexed.keys() - benchmark.keys())})"
            )
    cached = {}
    with paths["predictions"].open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            raw = json.loads(line, object_pairs_hook=_json_object)
            location = f"prediction cache line {number}"
            if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
                raise ValueError(f"{location}: invalid record/id")
            if raw["id"] in cached:
                raise ValueError(f"{location}: duplicate prediction id {raw['id']}")
            if raw.get("run_config_hash") != config_hash:
                raise ValueError(f"{location}: run_config_hash mismatch")
            cached[raw["id"]] = _scores(raw.get("sdg_scores"), location)
    if set(cached) != {key[0] for key in benchmark}:
        raise ValueError("prediction cache: id coverage mismatch against benchmark")
    joined = []
    for key, source in benchmark.items():
        result, jrc = results[key], baseline[key]
        location = f"row {key}"
        y = _bool(source["label"], location)
        if source["text"] != result["text"] or source["text"] != jrc["text"]:
            raise ValueError(f"{location}: text mismatch across row joins")
        if y != _bool(result["label"], location) or y != _bool(jrc["expected_label"], location):
            raise ValueError(f"{location}: label mismatch across row joins")
        prediction_list = ast.literal_eval(jrc["predictions"])
        if not isinstance(prediction_list, list):
            raise ValueError(f"{location}: baseline predictions must be a list")
        jrc_pred = key[1] in {_sdg(value, location) for value in prediction_list}
        if (
            jrc_pred != _bool(jrc["predicted_label"], location)
            or jrc_pred != _bool(result["jrc_pred"], location)
            or (jrc_pred == y) != _bool(jrc["is_correct"], location)
        ):
            raise ValueError(f"{location}: baseline prediction/correctness mismatch")
        scores = cached[key[0]]
        if _scores(ast.literal_eval(result["gpt_scores"]), location) != scores:
            raise ValueError(f"{location}: result score map differs from prediction cache")
        target = scores.get(key[1], 0.0)
        if float(result["gpt_target_score"]) != target:
            raise ValueError(f"{location}: target score mismatch against prediction cache")
        for threshold in range(1, 6):
            if _bool(result[f"gpt_pred_ge_{threshold}"], location) != (target >= threshold):
                raise ValueError(f"{location}: threshold {threshold} prediction mismatch")
        joined.append(
            {
                "id": key[0],
                "sdg": key[1],
                "text": source["text"],
                "label": y,
                "jrc_pred": jrc_pred,
                "score": target,
                "scores": scores,
            }
        )
    return joined, saved, paths


def _stats(y: np.ndarray, pred: np.ndarray, sdgs: np.ndarray) -> dict[str, Any]:
    per_sdg = []
    for sdg in range(1, 18):
        mask = sdgs == sdg
        per_sdg.append({"sdg": sdg, "n": int(mask.sum()), **metrics_from_confusion(confusion(y[mask], pred[mask]))})
    keys = ("accuracy", "precision", "recall", "f1", "tp", "fp", "tn", "fn")
    return {
        "micro": metrics_from_confusion(confusion(y, pred)),
        "per_sdg": per_sdg,
        "macro": {key: float(np.mean([row[key] for row in per_sdg])) for key in keys},
    }


def _metric_mismatches(expected: Any, actual: Any, path: str = "") -> list[dict[str, Any]]:
    """Compare every recomputed historical field; missing fields are mismatches."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        return [
            item
            for key, value in expected.items()
            for item in _metric_mismatches(value, actual.get(key), f"{path}.{key}".lstrip("."))
        ]
    if isinstance(expected, list) and isinstance(actual, list) and len(expected) == len(actual):
        return [
            item
            for index, value in enumerate(expected)
            for item in _metric_mismatches(value, actual[index], f"{path}[{index}]")
        ]
    if isinstance(expected, (float, int)) and not isinstance(expected, bool):
        matches = (
            isinstance(actual, (float, int))
            and not isinstance(actual, bool)
            and math.isfinite(actual)
            and math.isclose(expected, actual, rel_tol=0, abs_tol=1e-12)
        )
    else:
        matches = expected == actual
    return [] if matches else [{"field": path, "recomputed": expected, "saved": actual}]


def _provenance(repo_root: Path, paths: dict[str, Path], saved: dict[str, Any]) -> dict[str, Any]:
    """Read allowlisted source literals using AST; execute/import no project code."""
    files = dict(paths)
    for name, relative in {
        "harness_source": BENCHMARK_DIR / "run_honesty_classifier_sdg_benchmark.py",
        "constants_source": Path("honesty_scorer/constants.py"),
        "client_source": Path("honesty_scorer/client.py"),
        "normalization_source": Path("honesty_scorer/models.py"),
    }.items():
        if (repo_root / relative).is_file():
            files[name] = repo_root / relative
    result = {
        "files": {
            name: {
                "path": path.relative_to(repo_root).as_posix(),
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
            for name, path in files.items()
        },
        "cached_metadata": {
            key: saved.get(key)
            for key in ("model", "framing", "run_config_hash", "classifier_source", "sample_size", "sample_seed")
        },
        "runtime": {"python": platform.python_version(), "numpy": np.__version__},
        "source_config": {"status": "unavailable"},
    }
    if "client_source" in files:
        declared = {}
        try:
            client_tree = ast.parse(files["client_source"].read_text(encoding="utf-8"))
            for node in ast.walk(client_tree):
                if isinstance(node, ast.FunctionDef) and node.name == "_chat_json":
                    for assignment in node.body:
                        if isinstance(assignment, ast.Assign) and isinstance(assignment.value, ast.Dict):
                            for key, value in zip(assignment.value.keys, assignment.value.values):
                                if isinstance(key, ast.Constant) and key.value in ("temperature", "response_format"):
                                    declared[key.value] = ast.literal_eval(value)
        except (SyntaxError, ValueError, TypeError):
            declared = {}
        result["source_request_settings"] = {
            "literal_settings": declared,
            "scope": "Current client source declarations only; not archived request metadata. "
            "Resolved max_tokens and runtime model overrides are not recorded in the cache.",
        }
    if "constants_source" not in files:
        return result
    names = ("DEFAULT_OPENROUTER_MODEL", "SDG_MENTIONS_SYSTEM_PROMPT_GENERIC", "SDG_MENTIONS_USER_TEMPLATE_GENERIC")
    literals = {}
    try:
        tree = ast.parse(files["constants_source"].read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in names:
                        literals[target.id] = ast.literal_eval(node.value)
        if not all(isinstance(literals.get(name), str) for name in names):
            raise ValueError("generic prompt/model constants are not string literals")
    except (SyntaxError, ValueError, TypeError) as exc:
        result["source_config"] = {"status": "unavailable", "reason": str(exc)}
        return result
    model, system, user = (literals[name] for name in names)
    payload = {
        "model": model,
        "framing": "generic",
        "system_prompt_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest(),
        "user_template_sha256": hashlib.sha256(user.encode("utf-8")).hexdigest(),
        "benchmark_sha256": result["files"]["benchmark"]["sha256"],
        "response_schema": (
            "honesty_scorer.models.SdgMentionRecord (sdg_number, mention_count, importance_score, page_numbers)"
        ),
        "harness": "run_honesty_classifier_sdg_benchmark.py:v2",
    }
    reconstructed = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    result["source_config"] = {
        "status": "matched" if reconstructed == saved["run_config_hash"] and model == saved["model"] else "mismatch",
        "declared_model_matches_saved": model == saved["model"],
        "payload": payload,
        "reconstructed_run_config_hash": reconstructed,
        "system_prompt": system,
        "user_template": user,
        "method": "AST literal extraction; reconstruct historical v2 sorted-key JSON hash without executing source.",
        "caveat": "Source files are current local snapshots. A matching config hash binds the prompt/model declaration "
        "and benchmark bytes, but does not verify the provider backend or an environment model override.",
    }
    return result


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(repo_root: Path, output_dir: Path) -> dict:
    """Validate and reproduce fixed cached predictions; return the JSON report.

    Missing/misaligned/invalid input data raise before artifacts are written.
    Saved metric or current-source config discrepancies are recorded explicitly
    in the report, never repaired in the historical inputs.
    """
    repo_root, output_dir = Path(repo_root).resolve(), Path(output_dir).resolve()
    rows, saved, paths = _load_inputs(repo_root)
    y = np.array([row["label"] for row in rows])
    jrc = np.array([row["jrc_pred"] for row in rows])
    scores = np.array([row["score"] for row in rows])
    sdgs = np.array([row["sdg"] for row in rows])
    texts = [row["text"] for row in rows]
    thresholds = {f"gpt_priority_ge_{t}": _stats(y, scores >= t, sdgs) for t in range(1, 6)}
    rounded = np.rint(scores).astype(int)  # Historical pandas round: nearest even at ties.
    exact = {
        str(t): {
            "n": int(np.sum(rounded == t)),
            "precision_at_exact_score": float(np.mean(y[rounded == t])) if np.any(rounded == t) else None,
        }
        for t in range(1, 6)
    }
    row_ci = paired_bootstrap_f1(y, scores >= 3, jrc)
    cluster_ci = paired_bootstrap_f1(y, scores >= 3, jrc, texts=texts)
    only_a = int(np.sum(((scores >= 1) == y) & (jrc != y)))
    only_b = int(np.sum(((scores >= 1) != y) & (jrc == y)))
    chi2 = (abs(only_a - only_b) - 1) ** 2 / (only_a + only_b) if only_a + only_b else 0.0
    recomputed = {
        "n_rows": len(rows),
        "n_positive": int(y.sum()),
        "n_negative": int((~y).sum()),
        "jrc_sdg_mapper": _stats(y, jrc, sdgs),
        "gpt_oss_120b": thresholds,
        "priority_exact_score_precision": exact,
        "average_precision_priority_score": average_precision(y, scores),
        "jrc_average_precision_binary_score": average_precision(y, jrc.astype(float)),
        "topk_positive_capture": {
            f"top_{k}": sum(
                row["sdg"] in sorted(row["scores"], key=lambda s: (-row["scores"][s], s))[:k]
                for row in rows
                if row["label"]
            )
            / int(y.sum())
            if y.any()
            else 0.0
            for k in (1, 3, 5)
        },
        "paired_bootstrap_f1_gpt_ge_1_minus_jrc": paired_bootstrap_f1(y, scores >= 1, jrc),
        "paired_bootstrap_f1_gpt_ge_3_minus_jrc": row_ci,
        "mcnemar_correctness_gpt_ge_1_vs_jrc": {
            "only_a_correct": only_a,
            "only_b_correct": only_b,
            "chi2_cc": chi2,
            "p_approx": math.erfc(math.sqrt(chi2 / 2)),
        },
    }
    mismatches = _metric_mismatches(recomputed, saved)
    provenance = _provenance(repo_root, paths, saved)
    centrality = [
        {
            "score": float(score),
            "n": int(np.sum(scores == score)),
            "positive": int(np.sum(y & (scores == score))),
            "precision": float(np.mean(y[scores == score])),
        }
        for score in sorted(set(scores))
    ]
    missed = [
        {
            "id": row["id"],
            "sdg": row["sdg"],
            "score": row["score"],
            "jrc_missed": not row["jrc_pred"],
            "missed_thresholds": ";".join(str(t) for t in range(1, 6) if row["score"] < t),
        }
        for row in rows
        if row["label"] and (row["score"] < 5 or not row["jrc_pred"])
    ]
    threshold_rows = [
        {
            "model": "gpt_oss_120b",
            "threshold": t,
            **thresholds[f"gpt_priority_ge_{t}"]["micro"],
            "average_precision_continuous_score": recomputed["average_precision_priority_score"],
            "average_precision_binary_prediction": average_precision(y, (scores >= t).astype(float)),
        }
        for t in range(1, 6)
    ]
    threshold_rows.append(
        {
            "model": "jrc_sdg_mapper",
            "threshold": "binary",
            **recomputed["jrc_sdg_mapper"]["micro"],
            "average_precision_continuous_score": "",
            "average_precision_binary_prediction": recomputed["jrc_average_precision_binary_score"],
        }
    )
    summary = {
        "status": "matched" if not mismatches and provenance["source_config"]["status"] != "mismatch" else "mismatch",
        "comparison": "Fixed cached generic-domain SDG predictions; no fresh extraction or model calls.",
        "counts": {
            "rows": len(rows),
            "unique_ids": len({row["id"] for row in rows}),
            "unique_texts": len(set(texts)),
            "positive": int(y.sum()),
            "negative": int((~y).sum()),
            "text_cluster_size_counts": dict(sorted(Counter(Counter(texts).values()).items())),
        },
        "validation": {
            "row_joins": "passed",
            "cache_score_consistency": "passed",
            "saved_metrics": "matched" if not mismatches else "mismatch",
            "absolute_tolerance": 1e-12,
            "mismatches": mismatches,
        },
        "primary": {
            "threshold": 3,
            "gpt_micro": thresholds["gpt_priority_ge_3"]["micro"],
            "jrc_micro": recomputed["jrc_sdg_mapper"]["micro"],
            "observed_f1_difference": thresholds["gpt_priority_ge_3"]["micro"]["f1"]
            - recomputed["jrc_sdg_mapper"]["micro"]["f1"],
            "row_bootstrap": row_ci,
            "cluster_bootstrap": cluster_ci,
        },
        "thresholds": threshold_rows,
        "rounded_centrality_precision_historical": exact,
        "exact_centrality_precision": centrality,
        "missed_positives": {
            "target_score_zero": int(np.sum(y & (scores == 0))),
            "below_threshold": {str(t): int(np.sum(y & (scores < t))) for t in range(1, 6)},
            "jrc": int(np.sum(y & ~jrc)),
        },
        "historical_metrics_recomputed": recomputed,
        "procedures": {
            "joins": "Require unique (id, sdg) keys and identical full coverage, texts and labels across all CSVs; "
            "verify JRC list membership/correctness, cache ID coverage/config hashes, all score maps, "
            "target scores (absent SDG = 0), and five saved threshold flags. Use benchmark.csv row order.",
            "metrics": "Pool all text-SDG rows for micro accuracy, precision, recall and harmonic-mean F1; "
            "zero denominators return 0. Predict positive for raw centrality >= each threshold 1..5. "
            "AP weights precision at each tied-score cutoff by positives at that score / all positives, "
            "including score zero. Continuous-score AP is threshold independent; binary-prediction AP is "
            "also supplied for each threshold. It is not trapezoidal PR area.",
            "centrality": "Historical exact-score precision uses nearest-integer rounding with half ties to even "
            "(2.5 -> 2, 3.5 -> 4, 4.5 -> 4). Literal unrounded score precision, including zero, "
            "is separately reported. Missed positives are labelled-positive rows below each threshold.",
            "bootstrap": {
                "draws": BOOTSTRAP_DRAWS,
                "seed": BOOTSTRAP_SEED,
                "generator": "numpy.random.default_rng (PCG64), freshly seeded for each comparison",
                "quantiles": [0.025, 0.975],
                "quantile_method": "linear (numpy default)",
                "row": "Primary historical procedure: N integer indices sampled uniformly with replacement "
                "from N rows per draw; same indices for labels and both models; F1(A) minus F1(JRC).",
                "cluster": "Sensitivity: K integer indices sampled uniformly with replacement from K unique "
                "texts per draw; include all rows of every selected cluster with multiplicity for "
                "both models; compute pooled row-weighted micro F1, not mean cluster F1. The "
                "number of sampled rows can vary. Use raw centrality >=3 versus JRC.",
                "text_equality": TEXT_EQUALITY,
                "p_diff_le_0": "Empirical fraction of bootstrap differences <=0, not a calibrated p-value.",
            },
            "verification": "Compare every numeric historical field: counts, micro/macro/per-SDG metrics, rounded "
            "centrality precision, AP, top-k capture, row bootstrap at >=1 and >=3, and McNemar.",
        },
        "limitations": [
            "Thresholds 1-5 were explored on this same benchmark; >=3 is the reported operating point, not an "
            "independently selected or held-out optimum. The CIs do not account for threshold-selection uncertainty.",
            "The generic prompt removes bank-report framing. These results concern generic UN/policy text and do "
            "not establish bank-finance extraction validity, monetary-amount accuracy or Honesty Score validity.",
            "Both intervals condition on fixed cached predictions and this labelled sample. They omit model rerun "
            "variability, annotation error, training-data overlap and dependence beyond exact duplicate text. "
            "Cluster resampling assumes independence between unique texts; near duplicates and common sources "
            "can remain.",
            "Prediction JSONL contains only IDs, normalized SDG scores and run-config hashes; raw provider responses, "
            "request timestamps and a resolved backend snapshot are unavailable. Model metadata is a recorded "
            "declaration. "
            "Current source hashes are provenance, not proof that all current implementation bytes ran historically.",
        ],
        "provenance": provenance,
        "artifacts": {
            "summary": "benchmark_summary.json",
            "thresholds": "benchmark_thresholds.csv",
            "centrality": "benchmark_centrality.csv",
            "missed_positives": "benchmark_missed_positives.csv",
        },
    }
    # Refuse aliases to inputs (including symlinks/hard links) before writing anything.
    destinations = [output_dir / name for name in summary["artifacts"].values()]
    for destination in destinations:
        if any(
            destination.resolve() == path.resolve() or (destination.exists() and destination.samefile(path))
            for path in paths.values()
        ):
            raise ValueError("output artifact aliases an input file")
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(destinations[1], threshold_rows, list(threshold_rows[0]))
    _write_csv(destinations[2], centrality, ["score", "n", "positive", "precision"])
    _write_csv(destinations[3], missed, ["id", "sdg", "score", "jrc_missed", "missed_thresholds"])
    # Round-trip to ensure the returned object equals the on-disk JSON object.
    serialized = json.dumps(summary, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    destinations[0].write_text(serialized + "\n", encoding="utf-8")
    return json.loads(serialized)
