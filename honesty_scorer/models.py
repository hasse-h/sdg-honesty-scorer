"""Typed data contracts for extraction, scoring, and input manifests."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .constants import SDG_NUMBERS
from .validation import normalize_investment_item

PageText = Tuple[int, str]
JsonDict = Dict[str, Any]


@dataclass
class SdgMentionItem:
    sdg_number: int
    mention_count: int
    importance_score: float
    page_numbers: List[int]


@dataclass
class SdgMentions:
    sdg_data: List[SdgMentionItem] = field(default_factory=list)


@dataclass
class KeywordCategoryItem:
    category: str
    subcategories: List[str]
    amount_eur: float
    relevant_sdgs: List[int]
    justification: str = ""
    page_numbers: List[int] = field(default_factory=list)
    evidence: str = ""
    source_amount_text: str = ""
    source_value: Optional[float] = None
    source_unit: str = ""
    source_currency: str = ""
    construct_type: str = "unknown"
    sdg_support: str = "none"
    conversion_rate_used: Optional[float] = None
    conversion_source: str = ""
    needs_fx_review: bool = False
    inclusion_policy: str = "excluded"
    score_eligible: bool = False
    exclusion_reason: str = ""


@dataclass
class InvestmentInstrumentItem:
    instrument: str
    subcategories: List[str]
    amount_eur: float
    relevant_sdgs: List[int]
    justification: str = ""
    page_numbers: List[int] = field(default_factory=list)
    evidence: str = ""
    source_amount_text: str = ""
    source_value: Optional[float] = None
    source_unit: str = ""
    source_currency: str = ""
    construct_type: str = "unknown"
    sdg_support: str = "none"
    conversion_rate_used: Optional[float] = None
    conversion_source: str = ""
    needs_fx_review: bool = False
    inclusion_policy: str = "excluded"
    score_eligible: bool = False
    exclusion_reason: str = ""


@dataclass
class InvestmentCategorization:
    keyword_categories: List[KeywordCategoryItem] = field(default_factory=list)
    investment_instruments: List[InvestmentInstrumentItem] = field(default_factory=list)
    unlinked_investments_eur: float = 0.0


@dataclass(frozen=True)
class ReportInput:
    path: str
    bank: str
    country: str = ""
    year: str = ""
    report_type: str = ""

    @property
    def group_key(self) -> str:
        parts = [part for part in (self.country, self.bank, self.year) if part]
        return "_".join(parts) if parts else self.bank


class _BaseExtractionModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class SdgMentionRecord(_BaseExtractionModel):
    sdg_number: int
    mention_count: int = 0
    importance_score: float = 0.0
    page_numbers: List[int] = Field(default_factory=list)

    @field_validator("mention_count", mode="after")
    @classmethod
    def _non_negative_count(cls, value: int) -> int:
        return max(0, value)

    @field_validator("importance_score", mode="after")
    @classmethod
    def _clamp_importance(cls, value: float) -> float:
        return min(max(float(value), 0.0), 5.0)

    @field_validator("page_numbers", mode="before")
    @classmethod
    def _coerce_pages(cls, value: Any) -> List[int]:
        return _int_list(value)


class SdgMentionsResponse(_BaseExtractionModel):
    sdg_data: List[SdgMentionRecord] = Field(default_factory=list)


class InvestmentRecordMixin(_BaseExtractionModel):
    subcategories: List[str] = Field(default_factory=list)
    amount_eur: float = 0.0
    relevant_sdgs: List[int] = Field(default_factory=list)
    justification: str = ""
    page_numbers: List[int] = Field(default_factory=list)
    evidence: str = ""
    source_amount_text: str = ""
    source_value: Optional[float] = None
    source_unit: str = ""
    source_currency: str = ""
    construct_type: str = "unknown"
    sdg_support: str = "none"
    conversion_rate_used: Optional[float] = None
    conversion_source: str = ""
    needs_fx_review: bool = False
    inclusion_policy: str = "excluded"
    score_eligible: bool = False
    exclusion_reason: str = ""

    @field_validator("subcategories", mode="before")
    @classmethod
    def _coerce_subcategories(cls, value: Any) -> List[str]:
        return _string_list(value)

    @field_validator("amount_eur", mode="after")
    @classmethod
    def _non_negative_amount(cls, value: float) -> float:
        return max(0.0, float(value))

    @field_validator("source_value", "conversion_rate_used", mode="before")
    @classmethod
    def _coerce_optional_float(cls, value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            value = value.strip().replace(" ", "")
            if "," in value and "." not in value:
                parts = value.split(",")
                value = "".join(parts) if len(parts[-1]) == 3 else ".".join(parts)
            else:
                value = value.replace(",", "")
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @field_validator("relevant_sdgs", mode="before")
    @classmethod
    def _coerce_sdgs(cls, value: Any) -> List[int]:
        return _sdg_list(value)

    @field_validator("page_numbers", mode="before")
    @classmethod
    def _coerce_pages(cls, value: Any) -> List[int]:
        return _int_list(value)


class KeywordCategoryRecord(InvestmentRecordMixin):
    category: str = "Uncategorized"


class InvestmentInstrumentRecord(InvestmentRecordMixin):
    instrument: str = "Unspecified"


class InvestmentCategorizationResponse(_BaseExtractionModel):
    keyword_categories: List[KeywordCategoryRecord] = Field(default_factory=list)
    investment_instruments: List[InvestmentInstrumentRecord] = Field(default_factory=list)
    unlinked_investments_eur: float = 0.0

    @field_validator("unlinked_investments_eur", mode="after")
    @classmethod
    def _non_negative_unlinked(cls, value: float) -> float:
        return max(0.0, float(value))


def normalize_sdg_mentions(data: Any) -> List[JsonDict]:
    raw_items = data.get("sdg_data", data.get("mentions", [])) if isinstance(data, Mapping) else data
    if not isinstance(raw_items, list):
        raise RuntimeError("SDG mention response must contain a list")

    normalized = []
    for raw_item in raw_items:
        if not isinstance(raw_item, Mapping):
            continue
        try:
            record = SdgMentionRecord.model_validate(raw_item)
        except ValueError:
            continue
        if record.sdg_number not in SDG_NUMBERS:
            continue
        normalized.append(record.model_dump())
    return sorted(normalized, key=lambda item: item["sdg_number"])


def normalize_investment_categorization(data: Mapping[str, Any], report_year: str = "") -> JsonDict:
    response = InvestmentCategorizationResponse.model_validate(data)
    return {
        "keyword_categories": [
            normalize_investment_item(
                {
                    "category": item.category or "Uncategorized",
                    "subcategories": item.subcategories,
                    "amount_eur": item.amount_eur,
                    "relevant_sdgs": item.relevant_sdgs,
                    "justification": item.justification,
                    "page_numbers": item.page_numbers,
                    "evidence": item.evidence,
                    "source_amount_text": item.source_amount_text,
                    "source_value": item.source_value,
                    "source_unit": item.source_unit,
                    "source_currency": item.source_currency,
                    "construct_type": item.construct_type,
                    "sdg_support": item.sdg_support,
                    "conversion_rate_used": item.conversion_rate_used,
                    "conversion_source": item.conversion_source,
                    "needs_fx_review": item.needs_fx_review,
                    "inclusion_policy": item.inclusion_policy,
                    "score_eligible": item.score_eligible,
                    "exclusion_reason": item.exclusion_reason,
                },
                report_year,
            )
            for item in response.keyword_categories
        ],
        "investment_instruments": [
            normalize_investment_item(
                {
                    "instrument": item.instrument or "Unspecified",
                    "subcategories": item.subcategories,
                    "amount_eur": item.amount_eur,
                    "relevant_sdgs": item.relevant_sdgs,
                    "justification": item.justification,
                    "page_numbers": item.page_numbers,
                    "evidence": item.evidence,
                    "source_amount_text": item.source_amount_text,
                    "source_value": item.source_value,
                    "source_unit": item.source_unit,
                    "source_currency": item.source_currency,
                    "construct_type": item.construct_type,
                    "sdg_support": item.sdg_support,
                    "conversion_rate_used": item.conversion_rate_used,
                    "conversion_source": item.conversion_source,
                    "needs_fx_review": item.needs_fx_review,
                    "inclusion_policy": item.inclusion_policy,
                    "score_eligible": item.score_eligible,
                    "exclusion_reason": item.exclusion_reason,
                },
                report_year,
            )
            for item in response.investment_instruments
        ],
        "unlinked_investments_eur": response.unlinked_investments_eur,
    }


def report_from_path(path: str) -> ReportInput:
    import re

    bank = re.split(r"[_-]", Path(path).stem, maxsplit=1)[0]
    return ReportInput(path=path, bank=bank)


def _string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return []


def _sdg_list(value: Any) -> List[int]:
    return [number for number in _int_list(value) if number in SDG_NUMBERS]


def _int_list(value: Any) -> List[int]:
    if value is None:
        return []
    raw_values = value if isinstance(value, list) else [value]
    numbers = []
    for raw_value in raw_values:
        number = _optional_int(raw_value)
        if number is not None:
            numbers.append(number)
    return sorted(set(numbers))


def _optional_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
