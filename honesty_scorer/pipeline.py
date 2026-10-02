"""End-to-end report processing pipeline."""

from __future__ import annotations

import hashlib
import json
import logging
import time
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .client import AIClient
from .models import (
    InvestmentCategorization,
    InvestmentInstrumentItem,
    KeywordCategoryItem,
    PageText,
    ReportInput,
    SdgMentionItem,
    SdgMentions,
    report_from_path,
)
from .pdf import extract_text_from_pdf, load_parsed, parsed_path, save_parsed
from .score import empty_mentions, merge_mentions

LOGGER = logging.getLogger(__name__)


class BankProcessingError(RuntimeError):
    """Failure for one bank/report group, with partial extraction state."""

    def __init__(
        self,
        message: str,
        *,
        bank: str,
        mentions: SdgMentions | None = None,
        investments: InvestmentCategorization | None = None,
    ) -> None:
        super().__init__(message)
        self.bank = bank
        self.mentions = mentions
        self.investments = investments


def call_ai_sdg_mentions(client: AIClient, batch: list[PageText]) -> SdgMentions:
    """Call the model for one page batch and return normalized SDG mentions."""
    text = _page_labeled_text(batch)
    data = client.fetch_sdg_mentions(text)
    return SdgMentions([SdgMentionItem(**item) for item in data])


def call_ai_investment_categorization(client: AIClient, text: str, report_year: str = "") -> InvestmentCategorization:
    """Call the model for investment categorization and return dataclasses."""
    data = client.categorize_investments(text, report_year)
    keyword_categories = [KeywordCategoryItem(**item) for item in data.get("keyword_categories", [])]
    investment_instruments = [InvestmentInstrumentItem(**item) for item in data.get("investment_instruments", [])]
    return InvestmentCategorization(
        keyword_categories=keyword_categories,
        investment_instruments=investment_instruments,
        unlinked_investments_eur=float(data.get("unlinked_investments_eur", 0.0)),
    )


def merge_investment_categorizations(
    target: InvestmentCategorization,
    source: InvestmentCategorization,
) -> None:
    """Merge investment rows extracted from separate page chunks."""
    target.keyword_categories.extend(source.keyword_categories)
    target.investment_instruments.extend(source.investment_instruments)
    target.unlinked_investments_eur += source.unlinked_investments_eur


def process_bank_reports(
    client: AIClient,
    files: Iterable[str],
    **kwargs: Any,
) -> tuple[dict[str, SdgMentions], dict[str, InvestmentCategorization]]:
    """Process PDFs into SDG mention and investment maps keyed by legacy bank name."""
    return process_reports(client, [report_from_path(path) for path in files], **kwargs)


def process_reports(
    client: AIClient,
    reports: Iterable[ReportInput],
    *,
    checkpoint_dir: str | Path | None = None,
    resume: bool = False,
    on_error: str = "stop",
    max_workers: int = 4,
) -> tuple[dict[str, SdgMentions], dict[str, InvestmentCategorization]]:
    """Process PDFs into SDG mention and investment maps keyed by report group.

    ``checkpoint_dir`` enables one JSON checkpoint per completed bank/report
    group. With ``resume=True``, existing checkpoints are loaded and skipped.
    The default ``on_error='stop'`` preserves fail-loud historical behavior;
    successful prior bank checkpoints are still retained before the failure.
    """
    if on_error not in {"stop", "continue"}:
        raise ValueError("on_error must be 'stop' or 'continue'")

    checkpoint_path = Path(checkpoint_dir) if checkpoint_dir is not None else None
    if checkpoint_path is not None:
        checkpoint_path.mkdir(parents=True, exist_ok=True)

    banks_raw: dict[str, list[tuple[str, list[PageText]]]] = defaultdict(list)
    bank_years: dict[str, str] = {}
    for report in reports:
        cache = parsed_path(report.path)
        if _path_exists(cache):
            full_text, pages = load_parsed(cache)
        else:
            full_text, pages = extract_text_from_pdf(report.path)
            save_parsed(cache, full_text, pages)
        banks_raw[report.group_key].append((full_text, pages))
        if report.year:
            bank_years[report.group_key] = report.year

    mention_map: dict[str, SdgMentions] = {}
    investment_map: dict[str, InvestmentCategorization] = {}
    run_errors: list[BaseException] = []
    for bank, report_parts in banks_raw.items():
        checkpoint_file = _checkpoint_file(checkpoint_path, bank)
        if resume and checkpoint_file is not None and checkpoint_file.exists():
            LOGGER.info("bank_resume bank=%s checkpoint=%s", bank, checkpoint_file)
            mentions, investments = _read_bank_checkpoint(checkpoint_file)
            mention_map[bank] = mentions
            investment_map[bank] = investments
            continue

        pages = [page for _, report_pages in report_parts for page in report_pages]
        LOGGER.info("bank_start bank=%s reports=%d pages=%d", bank, len(report_parts), len(pages))
        try:
            mentions, investments = _process_single_bank(
                client, bank, pages, max_workers=max_workers, report_year=bank_years.get(bank, "")
            )
        except BankProcessingError as exc:
            if checkpoint_path is not None:
                _write_bank_error_checkpoint(checkpoint_path, exc)
            if on_error == "stop":
                raise
            LOGGER.exception("bank_failed bank=%s error=%s", bank, exc)
            run_errors.append(exc)
            continue

        mention_map[bank] = mentions
        investment_map[bank] = investments
        if checkpoint_file is not None:
            _write_bank_checkpoint(checkpoint_file, bank, mentions, investments)
        LOGGER.info("bank_complete bank=%s", bank)

    if run_errors:
        details = "; ".join(str(error) for error in run_errors)
        raise RuntimeError(f"Report processing completed with failed banks: {details}") from run_errors[0]
    return mention_map, investment_map


def _process_single_bank(
    client: AIClient,
    bank: str,
    pages: list[PageText],
    *,
    max_workers: int = 4,
    report_year: str = "",
) -> tuple[SdgMentions, InvestmentCategorization]:
    max_workers = max(1, max_workers)
    mention_result = empty_mentions()
    sdg_batches = _chunk_pages(pages)
    batch_errors: list[BaseException] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(_call_ai_sdg_mentions_logged, client, batch, bank, index, len(sdg_batches))
            for index, batch in enumerate(sdg_batches, start=1)
        ]
        for future in as_completed(futures):
            try:
                merge_mentions(mention_result, future.result())
            except Exception as exc:
                batch_errors.append(exc)
    if batch_errors:
        details = "; ".join(str(error) for error in batch_errors)
        raise BankProcessingError(
            f"SDG extraction failed for {bank}: {details}",
            bank=bank,
            mentions=mention_result,
        ) from batch_errors[0]

    investment_result = InvestmentCategorization()
    investment_errors: list[BaseException] = []
    investment_batches = _chunk_pages(pages)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(
                _call_ai_investment_categorization_logged,
                client,
                batch,
                bank,
                index,
                len(investment_batches),
                report_year,
            )
            for index, batch in enumerate(investment_batches, start=1)
        ]
        for future in as_completed(futures):
            try:
                merge_investment_categorizations(investment_result, future.result())
            except Exception as exc:
                investment_errors.append(exc)
    if investment_errors:
        details = "; ".join(str(error) for error in investment_errors)
        raise BankProcessingError(
            f"Investment categorization failed for {bank}: {details}",
            bank=bank,
            mentions=mention_result,
            investments=investment_result,
        ) from investment_errors[0]
    return mention_result, investment_result


def _call_ai_sdg_mentions_logged(
    client: AIClient,
    batch: list[PageText],
    bank: str,
    index: int,
    total: int,
) -> SdgMentions:
    text = _page_labeled_text(batch)
    LOGGER.info(
        "sdg_chunk_start bank=%s chunk=%d/%d chars=%d pages=%s",
        bank,
        index,
        total,
        len(text),
        _page_range(batch),
    )
    start = time.monotonic()
    try:
        data = client.fetch_sdg_mentions(text)
    except Exception:
        LOGGER.exception("sdg_chunk_failed bank=%s chunk=%d/%d", bank, index, total)
        raise
    LOGGER.info("sdg_chunk_complete bank=%s chunk=%d/%d seconds=%.2f", bank, index, total, time.monotonic() - start)
    return SdgMentions([SdgMentionItem(**item) for item in data])


def _call_ai_investment_categorization_logged(
    client: AIClient,
    batch: list[PageText],
    bank: str,
    index: int,
    total: int,
    report_year: str = "",
) -> InvestmentCategorization:
    text = _page_labeled_text(batch)
    LOGGER.info(
        "investment_chunk_start bank=%s chunk=%d/%d chars=%d pages=%s",
        bank,
        index,
        total,
        len(text),
        _page_range(batch),
    )
    start = time.monotonic()
    try:
        result = call_ai_investment_categorization(client, text, report_year)
    except Exception:
        LOGGER.exception("investment_chunk_failed bank=%s chunk=%d/%d", bank, index, total)
        raise
    LOGGER.info(
        "investment_chunk_complete bank=%s chunk=%d/%d seconds=%.2f",
        bank,
        index,
        total,
        time.monotonic() - start,
    )
    return result


def _chunk_pages(pages: list[PageText], max_chars: int = 15_000) -> list[list[PageText]]:
    chunks: list[list[PageText]] = []
    current: list[PageText] = []
    size = 0
    for page in pages:
        current.append(page)
        size += len(page[1])
        if size >= max_chars:
            chunks.append(current)
            current = []
            size = 0
    if current:
        chunks.append(current)
    return chunks


def _checkpoint_file(checkpoint_dir: Path | None, bank: str) -> Path | None:
    if checkpoint_dir is None:
        return None
    return checkpoint_dir / f"{_safe_checkpoint_stem(bank)}.json"


def _safe_checkpoint_stem(bank: str) -> str:
    normalized = unicodedata.normalize("NFKD", bank).encode("ascii", "ignore").decode("ascii")
    stem = "".join(character if character.isalnum() else "_" for character in normalized).strip("_")
    stem = "_".join(part for part in stem.split("_") if part) or "bank"
    digest = hashlib.sha256(bank.encode("utf-8")).hexdigest()[:12]
    return f"{stem[:80]}_{digest}"


def _write_bank_checkpoint(
    path: Path,
    bank: str,
    mentions: SdgMentions,
    investments: InvestmentCategorization,
) -> None:
    payload = {
        "bank": bank,
        "mentions": _mentions_to_json(mentions),
        "investments": _investments_to_json(investments),
    }
    _write_json_atomic(path, payload)
    stale_error_path = path.with_suffix(".error.json")
    if stale_error_path.exists():
        stale_error_path.unlink()


def _read_bank_checkpoint(path: Path) -> tuple[SdgMentions, InvestmentCategorization]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _mentions_from_json(payload["mentions"]), _investments_from_json(payload["investments"])


def _write_bank_error_checkpoint(checkpoint_dir: Path, error: BankProcessingError) -> None:
    payload = {
        "bank": error.bank,
        "error": str(error),
        "mentions": _mentions_to_json(error.mentions) if error.mentions is not None else None,
        "investments": _investments_to_json(error.investments) if error.investments is not None else None,
    }
    path = checkpoint_dir / f"{_safe_checkpoint_stem(error.bank)}.error.json"
    _write_json_atomic(path, payload)


def _mentions_to_json(mentions: SdgMentions) -> dict[str, Any]:
    return {"sdg_data": [asdict(item) for item in mentions.sdg_data]}


def _investments_to_json(investments: InvestmentCategorization) -> dict[str, Any]:
    return {
        "keyword_categories": [asdict(item) for item in investments.keyword_categories],
        "investment_instruments": [asdict(item) for item in investments.investment_instruments],
        "unlinked_investments_eur": investments.unlinked_investments_eur,
    }


def _mentions_from_json(payload: dict[str, Any]) -> SdgMentions:
    return SdgMentions([SdgMentionItem(**item) for item in payload.get("sdg_data", [])])


def _investments_from_json(payload: dict[str, Any]) -> InvestmentCategorization:
    return InvestmentCategorization(
        keyword_categories=[KeywordCategoryItem(**item) for item in payload.get("keyword_categories", [])],
        investment_instruments=[InvestmentInstrumentItem(**item) for item in payload.get("investment_instruments", [])],
        unlinked_investments_eur=float(payload.get("unlinked_investments_eur", 0.0)),
    )


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _page_range(pages: list[PageText]) -> str:
    if not pages:
        return ""
    numbers = [number for number, _ in pages]
    return f"{min(numbers)}-{max(numbers)}"


def _path_exists(path: str) -> bool:
    return Path(path).exists()


def _page_labeled_text(pages: list[PageText]) -> str:
    return "\n\n".join(f"[PAGE {number}]\n{page_text}" for number, page_text in pages)
