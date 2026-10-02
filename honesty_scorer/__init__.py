"""Public API for the SDG Honesty Scorer."""

from .client import AIClient
from .constants import DEFAULT_OPENROUTER_MODEL
from .excel import create_excel
from .excel import safe_excel_value as _safe_excel_value
from .models import (
    InvestmentCategorization,
    InvestmentInstrumentItem,
    KeywordCategoryItem,
    ReportInput,
    SdgMentionItem,
    SdgMentions,
)
from .pdf import discover_pdfs, extract_text_from_pdf, load_parsed, load_report_manifest, parsed_path, save_parsed
from .pipeline import call_ai_investment_categorization, call_ai_sdg_mentions, process_bank_reports, process_reports
from .score import compute_mismatch, honesty
from .score import merge_mentions as _merge_mentions

__all__ = [
    "AIClient",
    "DEFAULT_OPENROUTER_MODEL",
    "InvestmentCategorization",
    "InvestmentInstrumentItem",
    "KeywordCategoryItem",
    "ReportInput",
    "SdgMentionItem",
    "SdgMentions",
    "_merge_mentions",
    "_safe_excel_value",
    "call_ai_investment_categorization",
    "call_ai_sdg_mentions",
    "compute_mismatch",
    "create_excel",
    "discover_pdfs",
    "extract_text_from_pdf",
    "honesty",
    "load_parsed",
    "load_report_manifest",
    "parsed_path",
    "process_bank_reports",
    "process_reports",
    "save_parsed",
]
