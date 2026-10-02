"""PDF discovery, parsing, and cache helpers."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from pathlib import Path

from .models import PageText, ReportInput, report_from_path

try:
    import pdfplumber  # type: ignore
except Exception:
    pdfplumber = None


def extract_text_from_pdf(path: str) -> tuple[str, list[PageText]]:
    """Extract full text and per-page text from a PDF."""
    if not pdfplumber:
        raise RuntimeError("pdfplumber is required for PDF extraction")
    pages: list[PageText] = []
    full: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append((page.page_number, text))
            full.append(text)
    return "\n".join(full), pages


def parsed_path(path: str) -> str:
    """Return the cache path for parsed PDF text."""
    return f"{path}.parsed.json"


def load_parsed(path: str) -> tuple[str, list[PageText]]:
    """Load cached parsed text for a PDF."""
    with open(path, encoding="utf-8") as file:
        obj = json.load(file)
    return obj["full_text"], [(int(number), text) for number, text in obj["pages"]]


def save_parsed(path: str, full_text: str, pages: list[PageText]) -> None:
    """Cache parsed PDF text beside the input report."""
    with open(path, "w", encoding="utf-8") as file:
        json.dump({"full_text": full_text, "pages": pages}, file, ensure_ascii=False)


def discover_pdfs(paths: Iterable[str]) -> list[str]:
    """Expand directories into a flat list of PDF files."""
    pdfs: list[str] = []
    for path in paths:
        if os.path.isdir(path):
            for root, _dirs, files in os.walk(path):
                for filename in files:
                    if filename.lower().endswith(".pdf"):
                        pdfs.append(os.path.join(root, filename))
        else:
            pdfs.append(path)
    return sorted(pdfs)


def discover_reports(paths: Iterable[str]) -> list[ReportInput]:
    return [report_from_path(path) for path in discover_pdfs(paths)]


def load_report_manifest(path: str | Path) -> list[ReportInput]:
    """Load an explicit paper-run manifest.

    Supported columns are ``path``, ``bank``, ``country``, ``year``, and
    ``report_type``. Relative paths resolve relative to the manifest file.
    """
    import csv

    manifest_path = Path(path)
    root = manifest_path.parent
    reports: list[ReportInput] = []
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = {"path", "bank"} - set(reader.fieldnames or [])
        if missing:
            raise RuntimeError(f"Manifest missing required columns: {', '.join(sorted(missing))}")
        for line_number, row in enumerate(reader, start=2):
            report_path = Path(row["path"])
            if not report_path.is_absolute():
                report_path = root / report_path
            bank = (row.get("bank") or "").strip()
            if not bank:
                raise RuntimeError(f"Manifest row {line_number} has an empty bank value")
            reports.append(
                ReportInput(
                    path=str(report_path),
                    bank=bank,
                    country=(row.get("country") or "").strip(),
                    year=(row.get("year") or "").strip(),
                    report_type=(row.get("report_type") or "").strip(),
                )
            )
    return reports
