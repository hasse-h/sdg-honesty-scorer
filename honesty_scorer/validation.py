"""Deterministic validation for investment extraction records."""

from __future__ import annotations

import re
from typing import Any, Optional

FIXED_FX_SOURCE = "fixed_fx_table_2024-12-31"
FIXED_FX_TO_EUR = {
    "EUR": 1.0,
    "DKK": 0.134,
    "UAH": 0.024,
    "USD": 0.92,
    "GBP": 1.15,
    "SEK": 0.089,
    "NOK": 0.087,
}

# Per-report-year EUR conversion rates, derived from ECB daily reference rates
# (DKK/GBP/NOK/SEK/USD) and National Bank of Ukraine official rates (UAH), both
# sampled at the last available business day of each calendar year. Rates are
# expressed as "EUR received per 1 unit of foreign currency" (i.e. already
# inverted from the XXX-per-EUR quoting convention both sources publish in).
# Use these instead of FIXED_FX_TO_EUR whenever the report's year is known, so
# multi-year comparisons (especially UAH, which depreciated sharply against EUR
# across 2019-2024) are not distorted by applying a single modern-year rate.
YEARLY_FX_SOURCE = "ecb_nbu_year_end_reference_rate"
YEARLY_FX_TO_EUR: dict[str, dict[str, float]] = {
    "2019": {"DKK": 0.13384, "GBP": 1.17537, "NOK": 0.10138, "SEK": 0.09572, "USD": 0.89017, "UAH": 0.03785},
    "2020": {"DKK": 0.13439, "GBP": 1.11235, "NOK": 0.09551, "SEK": 0.09966, "USD": 0.81508, "UAH": 0.02879},
    "2021": {"DKK": 0.13447, "GBP": 1.19009, "NOK": 0.10011, "SEK": 0.09756, "USD": 0.88273, "UAH": 0.03234},
    "2022": {"DKK": 0.13447, "GBP": 1.12750, "NOK": 0.09511, "SEK": 0.08991, "USD": 0.93756, "UAH": 0.02567},
    "2023": {"DKK": 0.13418, "GBP": 1.15071, "NOK": 0.08897, "SEK": 0.09012, "USD": 0.90498, "UAH": 0.02369},
    "2024": {"DKK": 0.13409, "GBP": 1.20600, "NOK": 0.08478, "SEK": 0.08727, "USD": 0.96256, "UAH": 0.02276},
}
UNIT_MULTIPLIERS = {
    "actual": 1.0,
    "unit": 1.0,
    "units": 1.0,
    "thousand": 1_000.0,
    "thousands": 1_000.0,
    "k": 1_000.0,
    "million": 1_000_000.0,
    "millions": 1_000_000.0,
    "m": 1_000_000.0,
    "mn": 1_000_000.0,
    "meur": 1_000_000.0,
    "billion": 1_000_000_000.0,
    "billions": 1_000_000_000.0,
    "bn": 1_000_000_000.0,
    "trillion": 1_000_000_000_000.0,
    "trillions": 1_000_000_000_000.0,
    "tn": 1_000_000_000_000.0,
}
SCORABLE_CONSTRUCTS = {"disclosed_sdg_linked_finance"}
GROSS_CONTEXT_CONSTRUCTS = {
    "facilitated_sustainable_finance",
    "facilitated_on_behalf_of_customers",
    "gross_aum",
    "gross_sustainable_finance",
    "portfolio_balance",
    "taxonomy_denominator",
    "credit_limit_undrawn",
}
EXCLUDED_CONSTRUCTS = {
    "lending_portfolio_total",
    "market_share",
    "narrative_only",
    "portfolio_share_or_growth",
    "target",
    "forward_commitment",
    "recipient_side_financing",
    "unknown",
}
STRONG_SDG_SUPPORT = {"explicit", "strong"}
MAX_SCORABLE_EUR = 250_000_000_000.0


def normalize_investment_item(item: dict[str, Any], report_year: str = "") -> dict[str, Any]:
    """Populate source, conversion, and inclusion fields for one investment row.

    ``report_year`` selects the per-report-year FX rate table (``YEARLY_FX_TO_EUR``)
    for non-EUR conversions when known. If empty or not covered by the table, the
    conversion falls back to the fixed reproducible rates (``FIXED_FX_TO_EUR``).
    """
    output = dict(item)
    output["source_amount_text"] = str(output.get("source_amount_text") or "")
    output["source_value"] = _coerce_optional_float(output.get("source_value"))
    output["source_unit"] = _normalize_unit(output.get("source_unit"))
    output["source_currency"] = _normalize_currency(output.get("source_currency"))
    output["construct_type"] = _normalize_token(output.get("construct_type"), "unknown")
    output["sdg_support"] = _normalize_token(output.get("sdg_support"), "none")
    output["amount_eur"] = _coerce_float(output.get("amount_eur"), 0.0)
    output["conversion_rate_used"] = _coerce_optional_float(output.get("conversion_rate_used"))
    output["conversion_source"] = str(output.get("conversion_source") or "")
    output["needs_fx_review"] = bool(output.get("needs_fx_review") or False)
    _fill_source_fields_from_text(output)
    _fill_converted_amount(output, report_year)
    policy, eligible, reason = classify_inclusion(output)
    output["inclusion_policy"] = policy
    output["score_eligible"] = eligible
    output["exclusion_reason"] = reason
    return output


def classify_inclusion(item: dict[str, Any]) -> tuple[str, bool, str]:
    """Classify a row into score, gross-context, or excluded buckets."""
    construct = _normalize_token(item.get("construct_type"), "unknown")
    support = _normalize_token(item.get("sdg_support"), "none")
    amount = _coerce_float(item.get("amount_eur"), 0.0)
    sdgs = item.get("relevant_sdgs") if isinstance(item.get("relevant_sdgs"), list) else []
    page_numbers = item.get("page_numbers") if isinstance(item.get("page_numbers"), list) else []
    evidence = str(item.get("evidence") or "").strip()

    # A financing verb does not establish the amount drawn against a credit limit.
    if construct in GROSS_CONTEXT_CONSTRUCTS:
        return "gross_context_only", False, f"context_construct:{construct}"
    if construct == "unknown":
        return "excluded", False, "unknown_construct"
    if construct in EXCLUDED_CONSTRUCTS:
        return "excluded", False, f"excluded_construct:{construct}"
    if construct not in SCORABLE_CONSTRUCTS:
        return "excluded", False, f"unknown_construct:{construct}"
    if not page_numbers:
        return "excluded", False, "missing_page_numbers"
    if not evidence:
        return "excluded", False, "missing_evidence"
    if amount <= 0:
        return "excluded", False, "missing_amount"
    if not sdgs:
        return "gross_context_only", False, "missing_sdg_linkage"
    if support not in STRONG_SDG_SUPPORT:
        return "excluded", False, f"unsupported_sdg_linkage:{support}"
    if amount > MAX_SCORABLE_EUR:
        return "excluded", False, "implausible_magnitude"
    return "linked_scored", True, ""


def convert_source_amount_to_eur(
    source_value: Optional[float],
    source_unit: str,
    source_currency: str,
    report_year: str = "",
) -> tuple[Optional[float], Optional[float], str, bool]:
    """Convert a source amount to EUR, preferring the report's year-end rate.

    When ``report_year`` matches a year in ``YEARLY_FX_TO_EUR``, that year's
    ECB/NBU reference rate is used (methodology: rate at end of the report
    year). Otherwise falls back to the fixed reproducible rate table.
    """
    if source_value is None:
        return None, None, "", False
    unit = _normalize_unit(source_unit) or "actual"
    currency = _normalize_currency(source_currency) or "EUR"
    multiplier = UNIT_MULTIPLIERS.get(unit)
    if multiplier is None:
        return None, None, "", currency not in {"", "EUR"}
    if currency == "EUR":
        return round(source_value * multiplier, 2), 1.0, FIXED_FX_SOURCE, False
    year = str(report_year or "").strip()
    yearly_rates = YEARLY_FX_TO_EUR.get(year)
    if yearly_rates is not None and currency in yearly_rates:
        rate = yearly_rates[currency]
        amount = source_value * multiplier * rate
        return round(amount, 2), rate, f"{YEARLY_FX_SOURCE}:{year}", True
    rate = FIXED_FX_TO_EUR.get(currency)
    if rate is None:
        return None, None, "", True
    amount = source_value * multiplier * rate
    source_label = FIXED_FX_SOURCE if not year else f"{FIXED_FX_SOURCE}:fallback_unmapped_year_{year}"
    return round(amount, 2), rate, source_label, True


def _fill_source_fields_from_text(item: dict[str, Any]) -> None:
    text = item.get("source_amount_text", "")
    if item.get("source_value") is None:
        item["source_value"] = _parse_source_value(text)
    if not item.get("source_unit"):
        item["source_unit"] = _parse_source_unit(text)
    if not item.get("source_currency"):
        item["source_currency"] = _parse_source_currency(text)


def _fill_converted_amount(item: dict[str, Any], report_year: str = "") -> None:
    amount, rate, source, review = convert_source_amount_to_eur(
        item.get("source_value"), item.get("source_unit", ""), item.get("source_currency", ""), report_year
    )
    if amount is not None:
        item["amount_eur"] = amount
        item["conversion_rate_used"] = rate
        item["conversion_source"] = source
        item["needs_fx_review"] = review


def _normalize_unit(value: Any) -> str:
    token = _normalize_token(value, "")
    if token in {"€m", "eur_m", "eur_million", "million_eur", "millioneur"}:
        return "million"
    if token in {"€bn", "eur_bn", "eur_billion", "billion_eur", "billioneur"}:
        return "billion"
    if token in UNIT_MULTIPLIERS:
        return token
    return token


CURRENCY_ALIASES = {
    "EURO": "EUR",
    "EUROS": "EUR",
    "USDOLLAR": "USD",
    "USDOLLARS": "USD",
    "USDOLLARUSA": "USD",
    "DOLLAR": "USD",
    "DOLLARS": "USD",
    "POUND": "GBP",
    "POUNDS": "GBP",
    "POUNDSTERLING": "GBP",
    "POUNDSSTERLING": "GBP",
    "BRITISHPOUND": "GBP",
    "BRITISHPOUNDS": "GBP",
    "KRONE": "NOK",
    "KRONER": "NOK",
    "NORWEGIANKRONE": "NOK",
    "NORWEGIANKRONER": "NOK",
    "KRONA": "SEK",
    "SWEDISHKRONA": "SEK",
    "SWEDISHKRONOR": "SEK",
    "DANISHKRONE": "DKK",
    "DANISHKRONER": "DKK",
    "HRYVNIA": "UAH",
    "HRYVNIAS": "UAH",
    "UKRAINIANHRYVNIA": "UAH",
}


def _normalize_currency(value: Any) -> str:
    token = str(value or "").strip().upper().replace("€", "EUR")
    token = re.sub(r"[^A-Z]", "", token)
    return CURRENCY_ALIASES.get(token, token)


def _normalize_token(value: Any, default: str) -> str:
    token = str(value or "").strip().lower()
    token = re.sub(r"[^a-z0-9]+", "_", token).strip("_")
    return token or default


def _parse_source_value(text: str) -> Optional[float]:
    match = re.search(r"[-+]?\d[\d\s,]*(?:\.\d+)?", str(text))
    if not match:
        return None
    return _coerce_optional_float(match.group(0))


def _parse_source_unit(text: str) -> str:
    lowered = str(text).lower()
    if re.search(r"\b(thousand|thousands)\b", lowered):
        return "thousand"
    if re.search(r"\b(trillion|trillions|tn)\b", lowered):
        return "trillion"
    if re.search(r"\b(billion|billions|bn)\b", lowered):
        return "billion"
    if re.search(r"\b(million|millions|mn|meur)\b", lowered):
        return "million"
    return "actual"


def _parse_source_currency(text: str) -> str:
    match = re.search(r"\b(EUR|EUROS?|DKK|UAH|USD|GBP|SEK|NOK)\b|€", str(text), flags=re.IGNORECASE)
    if not match:
        return ""
    return _normalize_currency(match.group(0))


def _coerce_float(value: Any, default: float) -> float:
    converted = _coerce_optional_float(value)
    if converted is None:
        return default
    return max(0.0, converted)


def _coerce_optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = _normalize_number_string(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_number_string(value: str) -> str:
    clean = value.strip().replace(" ", "")
    if "," in clean and "." not in clean:
        parts = clean.split(",")
        if len(parts[-1]) == 3:
            return "".join(parts)
        return ".".join(parts)
    return clean.replace(",", "")
