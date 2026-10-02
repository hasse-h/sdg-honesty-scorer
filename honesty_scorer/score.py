"""Scoring helpers for SDG narrative-investment alignment."""

from __future__ import annotations

from .constants import MAX_MISMATCH, SDG_NUMBERS
from .models import InvestmentCategorization, SdgMentionItem, SdgMentions


def compute_mismatch(mentions: SdgMentions, investments: InvestmentCategorization) -> float:
    """Compute L1 mismatch between narrative centrality and linked SDG allocation.

    The financial denominator is linked SDG amount only. Unlinked investments are
    reported separately but do not enter the SDG profile denominator because they
    cannot be assigned to a specific SDG.
    """
    sdg_eur = _euros_by_sdg(investments)
    linked_total = sum(sdg_eur.values())
    mention_by_sdg = {item.sdg_number: item.importance_score for item in mentions.sdg_data}
    mismatch = 0.0
    for sdg_number in SDG_NUMBERS:
        share = sdg_eur.get(sdg_number, 0.0) / linked_total if linked_total else 0.0
        expected_importance = min(5.0 * share, 5.0)
        mismatch += abs(mention_by_sdg.get(sdg_number, 0.0) - expected_importance)
    return round(mismatch, 4)


def honesty(mismatch: float) -> float:
    """Convert mismatch into a 0-1 honesty score."""
    return round(max(0.0, 1.0 - mismatch / MAX_MISMATCH), 4)


def empty_mentions() -> SdgMentions:
    return SdgMentions(
        [
            SdgMentionItem(
                sdg_number=number,
                mention_count=0,
                importance_score=0.0,
                page_numbers=[],
            )
            for number in SDG_NUMBERS
        ]
    )


def merge_mentions(target: SdgMentions, source: SdgMentions) -> None:
    """Merge SDG mention records by SDG number."""
    target_by_sdg = {item.sdg_number: item for item in target.sdg_data}
    for source_item in source.sdg_data:
        target_item = target_by_sdg.get(source_item.sdg_number)
        if target_item is None:
            target.sdg_data.append(source_item)
            target_by_sdg[source_item.sdg_number] = source_item
            continue
        target_item.mention_count += source_item.mention_count
        target_item.importance_score = max(target_item.importance_score, source_item.importance_score)
        target_item.page_numbers = sorted(set(target_item.page_numbers + source_item.page_numbers))
    target.sdg_data.sort(key=lambda item: item.sdg_number)


def euros_by_sdg(investments: InvestmentCategorization) -> dict[int, float]:
    return _euros_by_sdg(investments)


def _euros_by_sdg(investments: InvestmentCategorization) -> dict[int, float]:
    output = {number: 0.0 for number in SDG_NUMBERS}
    for category in investments.keyword_categories:
        if not _score_eligible(category):
            continue
        for sdg_number in category.relevant_sdgs:
            output[sdg_number] += category.amount_eur
    for instrument in investments.investment_instruments:
        if not _score_eligible(instrument):
            continue
        for sdg_number in instrument.relevant_sdgs:
            output[sdg_number] += instrument.amount_eur
    return output


def _score_eligible(item: object) -> bool:
    return bool(getattr(item, "score_eligible", False)) and getattr(item, "inclusion_policy", "") == "linked_scored"
