"""Excel export for SDG honesty outputs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .constants import DANGEROUS_EXCEL_PREFIXES
from .metadata import metadata_rows
from .models import InvestmentCategorization, JsonDict, SdgMentions
from .score import compute_mismatch, euros_by_sdg, honesty

try:
    import openpyxl  # type: ignore
    import pandas as pd  # type: ignore
    from openpyxl.styles import Alignment, Font  # type: ignore
except Exception:
    openpyxl = pd = Alignment = Font = None


def create_excel(
    mention_map: dict[str, SdgMentions],
    investment_map: dict[str, InvestmentCategorization],
    output_file: str,
    run_metadata: Mapping[str, Any] | None = None,
) -> None:
    """Write summary, SDG mentions, investment categorization, and run metadata sheets."""
    if openpyxl is None or pd is None:
        raise RuntimeError("openpyxl and pandas are required for Excel export")
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        banks = sorted(mention_map.keys() & investment_map.keys())
        _write_summary_sheet(writer, banks, mention_map, investment_map)
        for bank in banks:
            _write_mentions_sheet(writer, bank, mention_map[bank])
            _write_keyword_sheet(writer, bank, investment_map[bank])
            _write_instrument_sheet(writer, bank, investment_map[bank])
        if run_metadata:
            dataframe = pd.DataFrame(_safe_excel_rows(metadata_rows(run_metadata)))
            dataframe.to_excel(writer, sheet_name="Run_Metadata", index=False)
            _style_sheet(writer.sheets["Run_Metadata"])


def _write_summary_sheet(
    writer: Any,
    banks: list[str],
    mention_map: dict[str, SdgMentions],
    investment_map: dict[str, InvestmentCategorization],
) -> None:
    rows = []
    for bank in banks:
        investments = investment_map[bank]
        mismatch = compute_mismatch(mention_map[bank], investments)
        linked_eur = sum(euros_by_sdg(investments).values())
        rows.append(
            {
                "bank": bank,
                "mismatch": mismatch,
                "honesty_score": honesty(mismatch),
                "linked_investments_eur": linked_eur,
                "gross_context_investments_eur": _amount_by_policy(investments, "gross_context_only"),
                "excluded_investments_eur": _amount_by_policy(investments, "excluded"),
                "unlinked_investments_eur": investments.unlinked_investments_eur,
            }
        )
    dataframe = pd.DataFrame(_safe_excel_rows(rows))
    dataframe.to_excel(writer, sheet_name="Summary", index=False)
    _style_sheet(writer.sheets["Summary"])


def _write_mentions_sheet(writer: Any, bank: str, mentions: SdgMentions) -> None:
    rows = [
        {
            "sdg_number": item.sdg_number,
            "mention_count": item.mention_count,
            "importance_score": item.importance_score,
            "page_numbers": ", ".join(map(str, item.page_numbers)),
        }
        for item in mentions.sdg_data
    ]
    dataframe = pd.DataFrame(_safe_excel_rows(rows))
    sheet = _sheet_name(bank, "Mentions")
    dataframe.to_excel(writer, sheet_name=sheet, index=False)
    _style_sheet(writer.sheets[sheet])


def _write_keyword_sheet(writer: Any, bank: str, investments: InvestmentCategorization) -> None:
    rows = [
        {
            "category": category.category,
            "subcategories": ", ".join(category.subcategories),
            "amount_eur": category.amount_eur,
            "source_amount_text": category.source_amount_text,
            "source_value": category.source_value,
            "source_unit": category.source_unit,
            "source_currency": category.source_currency,
            "construct_type": category.construct_type,
            "sdg_support": category.sdg_support,
            "conversion_rate_used": category.conversion_rate_used,
            "conversion_source": category.conversion_source,
            "needs_fx_review": category.needs_fx_review,
            "inclusion_policy": category.inclusion_policy,
            "score_eligible": category.score_eligible,
            "exclusion_reason": category.exclusion_reason,
            "relevant_sdgs": ", ".join(map(str, category.relevant_sdgs)),
            "justification": category.justification,
            "page_numbers": ", ".join(map(str, category.page_numbers)),
            "evidence": category.evidence,
        }
        for category in investments.keyword_categories
    ]
    dataframe = pd.DataFrame(_safe_excel_rows(rows))
    sheet = _sheet_name(bank, "Keywords")
    dataframe.to_excel(writer, sheet_name=sheet, index=False)
    _style_sheet(writer.sheets[sheet])


def _write_instrument_sheet(writer: Any, bank: str, investments: InvestmentCategorization) -> None:
    rows = [
        {
            "instrument": instrument.instrument,
            "subcategories": ", ".join(instrument.subcategories),
            "amount_eur": instrument.amount_eur,
            "source_amount_text": instrument.source_amount_text,
            "source_value": instrument.source_value,
            "source_unit": instrument.source_unit,
            "source_currency": instrument.source_currency,
            "construct_type": instrument.construct_type,
            "sdg_support": instrument.sdg_support,
            "conversion_rate_used": instrument.conversion_rate_used,
            "conversion_source": instrument.conversion_source,
            "needs_fx_review": instrument.needs_fx_review,
            "inclusion_policy": instrument.inclusion_policy,
            "score_eligible": instrument.score_eligible,
            "exclusion_reason": instrument.exclusion_reason,
            "relevant_sdgs": ", ".join(map(str, instrument.relevant_sdgs)),
            "justification": instrument.justification,
            "page_numbers": ", ".join(map(str, instrument.page_numbers)),
            "evidence": instrument.evidence,
        }
        for instrument in investments.investment_instruments
    ]
    dataframe = pd.DataFrame(_safe_excel_rows(rows))
    sheet = _sheet_name(bank, "Instruments")
    dataframe.to_excel(writer, sheet_name=sheet, index=False)
    _style_sheet(writer.sheets[sheet])


def _style_sheet(sheet: Any) -> None:
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")
    for column in sheet.columns:
        width = max(len(str(cell.value or "")) for cell in column) + 2
        sheet.column_dimensions[column[0].column_letter].width = min(width, 80)


def _sheet_name(bank: str, suffix: str) -> str:
    """Build a valid Excel sheet name that preserves the semantic suffix."""
    suffix_text = f"_{suffix}"
    max_bank_length = 31 - len(suffix_text)
    return f"{bank[:max_bank_length]}{suffix_text}"


def safe_excel_rows(rows: list[JsonDict]) -> list[JsonDict]:
    return _safe_excel_rows(rows)


def safe_excel_value(value: Any) -> Any:
    return _safe_excel_value(value)


def _amount_by_policy(investments: InvestmentCategorization, policy: str) -> float:
    rows = [*investments.keyword_categories, *investments.investment_instruments]
    return sum(item.amount_eur for item in rows if item.inclusion_policy == policy)


def _safe_excel_rows(rows: list[JsonDict]) -> list[JsonDict]:
    """Escape untrusted strings before writing them to Excel."""
    return [{key: _safe_excel_value(value) for key, value in row.items()} for row in rows]


def _safe_excel_value(value: Any) -> Any:
    """Escape strings that spreadsheet apps may interpret as formulas."""
    if isinstance(value, str) and value.lstrip().startswith(DANGEROUS_EXCEL_PREFIXES):
        return f"'{value}"
    return value
