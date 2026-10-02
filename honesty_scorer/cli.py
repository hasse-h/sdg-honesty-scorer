"""Command-line interface for the SDG Honesty Scorer."""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Optional

from .client import AIClient
from .constants import DEFAULT_OPENROUTER_MODEL
from .excel import create_excel
from .metadata import build_run_metadata
from .models import ReportInput
from .pdf import discover_pdfs, discover_reports, load_report_manifest
from .pipeline import process_reports


def main(
    paths: list[str],
    model: Optional[str] = None,
    output_file: Optional[str] = None,
    *,
    checkpoint_dir: Optional[str] = None,
    resume: bool = False,
    on_error: str = "stop",
    max_workers: int = 4,
) -> None:
    """Run the SDG honesty scorer CLI using legacy path discovery."""
    reports = discover_reports(paths)
    _run(
        reports=reports,
        model=model,
        output_file=output_file,
        checkpoint_dir=checkpoint_dir,
        resume=resume,
        on_error=on_error,
        max_workers=max_workers,
    )


def run_manifest(
    manifest: str,
    model: Optional[str] = None,
    output_file: Optional[str] = None,
    *,
    checkpoint_dir: Optional[str] = None,
    resume: bool = False,
    on_error: str = "stop",
    max_workers: int = 4,
) -> None:
    reports = load_report_manifest(manifest)
    _run(
        reports=reports,
        model=model,
        output_file=output_file,
        checkpoint_dir=checkpoint_dir,
        resume=resume,
        on_error=on_error,
        max_workers=max_workers,
    )


def cli_main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _configure_logging(args.log_level)
    if args.manifest:
        run_manifest(
            args.manifest,
            model=args.model,
            output_file=args.output,
            checkpoint_dir=args.checkpoint_dir,
            resume=args.resume,
            on_error=args.on_error,
            max_workers=args.max_workers,
        )
    else:
        main(
            args.paths,
            model=args.model,
            output_file=args.output,
            checkpoint_dir=args.checkpoint_dir,
            resume=args.resume,
            on_error=args.on_error,
            max_workers=args.max_workers,
        )
    return 0


def _run(
    reports: Iterable[ReportInput],
    model: Optional[str],
    output_file: Optional[str],
    *,
    checkpoint_dir: Optional[str] = None,
    resume: bool = False,
    on_error: str = "stop",
    max_workers: int = 4,
) -> None:
    reports = list(reports)
    client = AIClient(model=model)
    mention_map, investment_map = process_reports(
        client,
        reports,
        checkpoint_dir=checkpoint_dir,
        resume=resume,
        on_error=on_error,
        max_workers=max_workers,
    )
    common_banks = set(mention_map) & set(investment_map)
    if not common_banks:
        print("Nothing processed")
        return
    filename = output_file or f"sdg_analysis_{'_'.join(sorted(common_banks))}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    input_files = [report.path for report in reports]
    metadata = build_run_metadata(client.model, input_files, root=Path(__file__).resolve().parents[1])
    create_excel(mention_map, investment_map, filename, run_metadata=metadata)
    print(f"Report saved to {filename}")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyse bank SDG honesty")
    parser.add_argument("paths", nargs="*", help="PDF files or directories containing bank reports")
    parser.add_argument(
        "--manifest",
        help=(
            "CSV manifest with path, bank, country, year, and report_type columns. "
            "Relative paths resolve from the manifest."
        ),
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_OPENROUTER_MODEL,
        help=f"OpenRouter model id. Defaults to {DEFAULT_OPENROUTER_MODEL}.",
    )
    parser.add_argument("--output", help="Output .xlsx path. Defaults to a timestamped filename.")
    parser.add_argument(
        "--checkpoint-dir",
        help="Directory for per-bank JSON checkpoints and error markers. Enables resumable long runs.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse completed per-bank checkpoints from --checkpoint-dir.",
    )
    parser.add_argument(
        "--on-error",
        choices=["stop", "continue"],
        default="stop",
        help="Stop at first failed bank or continue writing checkpoints and exit non-zero after failures.",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("HONESTY_LOG_LEVEL", "INFO"),
        help="Python logging level for progress output. Defaults to HONESTY_LOG_LEVEL or INFO.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Concurrent model calls per bank for SDG and investment chunks. Defaults to 4.",
    )
    args = parser.parse_args(argv)
    if not args.manifest and not args.paths:
        parser.error("provide at least one path or --manifest")
    if args.manifest and args.paths:
        parser.error("use either positional paths or --manifest, not both")
    if args.resume and not args.checkpoint_dir:
        parser.error("--resume requires --checkpoint-dir")
    if not args.output and args.paths:
        args.paths = discover_pdfs(args.paths)
    return args


def _configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
