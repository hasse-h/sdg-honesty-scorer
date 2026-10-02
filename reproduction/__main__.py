"""Rebuild study results from saved predictions, without model calls."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import socket
from pathlib import Path


def input_paths(repo: Path) -> list[Path]:
    """Return every frozen analytical input, excluding original copyrighted PDFs."""
    paths = list((repo / "data/bank_reports/manifests").glob("bank_reports_*.csv"))
    run_root = repo / "evaluations/reruns/country_year_classification_20260630_211343"
    for name in ("checkpoints", "checkpoints_corrected"):
        paths.extend(run_root.glob(f"*/{name}/*.json"))
    bench = repo / "evaluations/sdg_benchmark"
    paths.extend(
        bench / name
        for name in (
            "benchmark.csv",
            "sdg_mapper_results.csv",
            "gpt_oss_120b_generic_results.csv",
            "gpt_oss_120b_generic_predictions.jsonl",
            "gpt_oss_120b_vs_jrc_generic_metrics.json",
        )
    )
    paths.extend(
        repo / name
        for name in (
            "evaluations/fusion_open_items_adjudication_20260701/before_after_totals.json",
            "evaluations/section45_full_window_20260708/sdg_profiles_by_country_year.csv",
            "evaluations/section45_full_window_20260708/sdg_profiles_pooled_2019_2024.csv",
            "reproduction/finance_adjudications.json",
            "reproduction/finance_tag_adjudications.json",
            "reproduction/bank_year_exclusions.json",
            "reproduction/source_year_audit.json",
        )
    )
    return sorted(set(paths))


def input_checksums(repo: Path) -> dict[str, str]:
    return {p.relative_to(repo).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in input_paths(repo)}


def _deny_network(*args: object, **kwargs: object) -> None:
    raise RuntimeError("Study reproduction is offline: network access is disabled")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reproduction/output"))
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    locked = json.loads((repo / "reproduction/input_checksums.json").read_text())
    observed = input_checksums(repo)
    if observed != locked:
        changed = sorted(k for k in observed.keys() | locked.keys() if observed.get(k) != locked.get(k))
        raise ValueError("Frozen inputs are missing, added, or changed: " + ", ".join(changed))
    socket.socket.connect = _deny_network
    socket.create_connection = _deny_network
    from reproduction import adjudication, banks, benchmark, figures

    primary, excluded, audit = adjudication.load(repo)

    output.mkdir(parents=True, exist_ok=True)
    result = {
        "bank_analysis": banks.run(repo, output / "banks", primary_overrides=primary, excluded_bank_years=excluded),
        "source_adjudication": audit,
        "benchmark": benchmark.run(repo, output / "benchmark"),
        "environment": {
            "python": platform.python_version(),
            "packages": {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "matplotlib")},
        },
        "input_sha256": observed,
        "network": "disabled; no API credentials or model calls are used",
    }
    figures.run(output)
    (output / "reproduction_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(f"Reproduced bank statistics, benchmark metrics, sensitivity analyses and figures in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
