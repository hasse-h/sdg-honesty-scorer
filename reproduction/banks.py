"""Reproduce the bank analysis offline from immutable, cached classifications.

Only ``run`` writes files, exclusively inside its caller-supplied output directory.
No scorer imports, model calls, PDF reads, FX conversion, or reclassification occur.
``finance_eur`` in composition tables is *tagged exposure*, not conserved money.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

COUNTRIES = ("finland", "ukraine")
YEARS = tuple(range(2019, 2025))
SDGS = tuple(range(1, 18))
SECTIONS = ("keyword_categories", "investment_instruments")
RUN_PATH = Path("evaluations/reruns/country_year_classification_20260630_211343")
MANIFEST_PATH = Path("data/bank_reports/manifests")
TOTALS_PATH = Path("evaluations/fusion_open_items_adjudication_20260701/before_after_totals.json")
PROFILE_PATH = Path("evaluations/section45_full_window_20260708")
CREDIT_LIMIT_TEXT = re.compile(r"credit[\s\-\u2011]+limits?|undrawn", re.IGNORECASE)
AUDIT_FIELDS = (
    "country",
    "year",
    "bank",
    "source_checkpoint",
    "section",
    "index",
    "amount_eur",
    "evidence",
    "page_numbers",
    "relevant_sdgs",
    "construct_type",
    "original_score_eligible",
    "original_inclusion_policy",
    "original_exclusion_reason",
    "legacy_eligible",
    "primary_eligible",
    "approved_amount_eur",
    "approved_relevant_sdgs",
    "source_adjudication_reason",
    "impacted_by_strict_undrawn_exclusion",
    "primary_exclusion_reason",
    "credit_limit_evidence_requires_separate_adjudication",
)

DEFINITIONS = {
    "primary_eligibility": "Cached score_eligible is true AND inclusion_policy=linked_scored "
    "AND construct_type != credit_limit_undrawn. No other row is reclassified.",
    "legacy_inclusion": "Cached score_eligible AND linked_scored, preserving historical "
    "financing-verb exceptions. Does not rerun today's classify_inclusion.",
    "eligible_unique_amount_eur": "Sum of eligible cached row amounts, once per row, before SDG expansion. "
    "Unique means unexpanded rows, not a new economic-instrument deduplication.",
    "financial_items": "All extracted rows in keyword_categories and investment_instruments, "
    "including excluded and gross-context rows; raw and corrected counts are reported separately.",
    "source_file_count": "Number of report paths in the canonical country-year manifest; "
    "reports are not opened or required for this cached reproduction.",
    "retained_mentions": "Sum of cached mention_count for SDGs whose maximum cached centrality meets threshold.",
    "R": "Maximum cached importance_score per bank-year-SDG; values below threshold become zero. "
    "Primary threshold is 3. R is not count-weighted.",
    "A": "Each eligible row's full amount goes to every distinct SDG tag; fractional sensitivity "
    "instead divides that row's amount equally among its distinct tags.",
    "primary_score_scale": "E=5*A/sum(A), or zero when finance is zero; M=sum(abs(R-E)); AS=1-M/85.",
    "silent": "Both sum(R) and sum(A) are zero. Primary AS=1 mechanically; excluded from non-silent means.",
    "composition": "Country-year narrative weights=sum(mention_count*centrality) for retained SDGs. "
    "Normalize narrative weights and tagged exposures separately; gap_pp=100*(narrative_share-finance_share). "
    "These are composition profiles, not the bank-year score's R vector.",
    "finance_eur": "TAGGED EXPOSURE, NOT CONSERVED MONEY: full amount counted at each distinct SDG tag.",
    "normalized_allocated_eur_for_display": "DISPLAY-ONLY conserved rescaling: country-year unique eligible "
    "row amount * tagged-exposure share; not an instrument-level fractional allocation or an observed SDG amount.",
    "normalized_score_scale": "R'=5*R/sum(R), or zero if narrative absent; normalized_L1=sum(abs(R'-E)); "
    "normalized_alignment=1-normalized_L1/10. Both-zero is undefined/excluded; one-sided-zero alignment is 0.5. "
    "This symmetric normalized scale and primary AS have different denominators and are not directly comparable.",
    "precision": "All calculations and aggregation use unrounded values. Only manuscript display "
    "rounds M/AS to four decimals (bank AS display follows scorer's rounded-M conversion), money to cents, "
    "and composition gap display to one decimal. CSV/JSON analytical values retain precision.",
    "correlation": "Pearson correlation between AS and retained_mentions among non-silent bank-years; "
    "undefined for fewer than two observations or either constant variable. No p-value is claimed.",
    "identities": "Exact manifest bank labels; no Alisa/Evli/Fellow consolidation or predecessor inference. "
    "Report basenames document predecessor-labelled sources without asserting legal continuity.",
    "panels": "Complete identities appear in all six years. Excluding both-zero observations from those "
    "identities can unbalance the panel; a separate never-both-zero panel stays complete and balanced.",
}


@dataclass
class BankYear:
    country: str
    year: int
    bank: str
    source_checkpoint: str
    raw_checkpoint: str
    manifest: str
    reports: list[dict[str, str]]
    corrected: dict[str, Any]
    raw: dict[str, Any]

    def identity(self) -> dict[str, Any]:
        return {"country": self.country, "year": self.year, "bank": self.bank}


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON input: {path}: {exc}") from exc


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _number(value: Any, label: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"Invalid nonnegative finite {label}: {value!r}")
    return number


def _sdg(value: Any) -> int:
    number = int(value)
    if number not in SDGS or float(value) != number:
        raise ValueError(f"Invalid SDG: {value!r}")
    return number


def _finance_rows(data: dict[str, Any]):
    for section in SECTIONS:
        for index, row in enumerate(data["investments"][section]):
            yield section, index, row


def _legacy_eligible(row: dict[str, Any]) -> bool:
    return row["score_eligible"] is True and row["inclusion_policy"] == "linked_scored"


def _eligible(row: dict[str, Any], strict: bool = True) -> bool:
    return _legacy_eligible(row) and (not strict or row["construct_type"] != "credit_limit_undrawn")


def _validate_checkpoint(data: dict[str, Any], path: Path) -> None:
    try:
        if not isinstance(data["mentions"]["sdg_data"], list):
            raise ValueError("mentions.sdg_data must be a list")
        for row in data["mentions"]["sdg_data"]:
            _sdg(row["sdg_number"])
            if _number(row["importance_score"], "centrality") > 5:
                raise ValueError("centrality exceeds 5")
            count = _number(row["mention_count"], "mention_count")
            if count != int(count):
                raise ValueError("mention_count must be an integer")
        for section in SECTIONS:
            if not isinstance(data["investments"][section], list):
                raise ValueError(f"investments.{section} must be a list")
        for _, _, row in _finance_rows(data):
            amount = _number(row["amount_eur"], "amount_eur")
            if not isinstance(row["score_eligible"], bool):
                raise ValueError("score_eligible must be a cached boolean")
            for field in ("construct_type", "inclusion_policy"):
                if not isinstance(row[field], str):
                    raise ValueError(f"{field} must be a string")
            if not isinstance(row["relevant_sdgs"], list):
                raise ValueError("relevant_sdgs must be a list")
            tags = {_sdg(s) for s in row["relevant_sdgs"]}
            if _legacy_eligible(row) and (not tags or amount <= 0):
                raise ValueError("cached eligible row has no SDG tags or positive amount")
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Malformed checkpoint {path}: {exc}") from exc


def _load_checkpoints(directory: Path, expected: dict[str, str], root: Path):
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise FileNotFoundError(f"Missing checkpoints: {directory}")
    found = {}
    for path in paths:
        data = _read_json(path)
        _validate_checkpoint(data, path)
        identifier = data.get("bank")
        if identifier not in expected:
            raise ValueError(f"Checkpoint bank {identifier!r} does not match exact manifest identities: {path}")
        bank = expected[identifier]
        if bank in found:
            raise ValueError(f"Duplicate bank-year checkpoint for {bank}: {directory}")
        found[bank] = (path.relative_to(root).as_posix(), data)
    missing = set(expected.values()) - set(found)
    if missing:
        raise FileNotFoundError(f"Missing bank-year checkpoints in {directory}: {sorted(missing)}")
    return found


def _load_inputs(root: Path) -> tuple[list[BankYear], list[str]]:
    records, inputs = [], []
    for country in COUNTRIES:
        for year in YEARS:
            stem = f"{country}_{year}"
            manifest = MANIFEST_PATH / f"bank_reports_{stem}.csv"
            reports = _read_csv(root / manifest)
            if not reports:
                raise ValueError(f"Empty manifest: {manifest}")
            by_bank = defaultdict(list)
            expected, source_paths = {}, set()
            for row in reports:
                if not {"path", "bank", "country", "year", "report_type"}.issubset(row):
                    raise ValueError(f"Missing manifest columns: {manifest}")
                if row["country"].lower() != country or row["year"] != str(year) or not row["bank"]:
                    raise ValueError(f"Manifest identity mismatch: {manifest}: {row}")
                if not row["path"] or row["path"] in source_paths:
                    raise ValueError(f"Empty or duplicate source report path: {manifest}: {row['path']}")
                source_paths.add(row["path"])
                by_bank[row["bank"]].append(row)
                expected[f"{row['country']}_{row['bank']}_{year}"] = row["bank"]
            corrected = _load_checkpoints(root / RUN_PATH / stem / "checkpoints_corrected", expected, root)
            raw = _load_checkpoints(root / RUN_PATH / stem / "checkpoints", expected, root)
            inputs.append(manifest.as_posix())
            for bank in sorted(by_bank):
                cp_path, cp = corrected[bank]
                raw_path, before = raw[bank]
                inputs.extend((cp_path, raw_path))
                records.append(
                    BankYear(country, year, bank, cp_path, raw_path, manifest.as_posix(), by_bank[bank], cp, before)
                )
    return records, inputs


def _analyze(
    data: dict[str, Any], *, strict: bool = True, fractional: bool = False, threshold: int = 3
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    centrality = dict.fromkeys(SDGS, 0.0)
    counts = dict.fromkeys(SDGS, 0)
    for row in data["mentions"]["sdg_data"]:
        s = _sdg(row["sdg_number"])
        centrality[s] = max(centrality[s], float(row["importance_score"]))
        counts[s] += int(row["mention_count"])
    narrative = {s: v if v >= threshold else 0.0 for s, v in centrality.items()}
    amounts = {s: [] for s in SDGS}
    eligible_amounts = []
    items = list(_finance_rows(data))
    for _, _, row in items:
        if not _eligible(row, strict):
            continue
        tags = sorted({_sdg(s) for s in row["relevant_sdgs"]})
        amount = float(row["amount_eur"])
        eligible_amounts.append(amount)
        for s in tags:
            amounts[s].append(amount / len(tags) if fractional else amount)
    finance = {s: math.fsum(v) for s, v in amounts.items()}
    total_finance, total_narrative = math.fsum(finance.values()), math.fsum(narrative.values())
    expected = {s: 5 * v / total_finance if total_finance else 0.0 for s, v in finance.items()}
    normalized = {s: 5 * v / total_narrative if total_narrative else 0.0 for s, v in narrative.items()}
    mismatch = math.fsum(abs(narrative[s] - expected[s]) for s in SDGS)
    normalized_l1 = math.fsum(abs(normalized[s] - expected[s]) for s in SDGS)
    silent = total_narrative == 0 and total_finance == 0
    sdg_rows = [
        {
            "sdg": s,
            "cached_centrality": centrality[s],
            "mention_count": counts[s],
            "retained_mentions": counts[s] if centrality[s] >= threshold else 0,
            "R": narrative[s],
            "A_eur": finance[s],
            "E": expected[s],
            "narrative_weight": counts[s] * narrative[s],
            "absolute_mismatch": abs(narrative[s] - expected[s]),
            "normalized_R": normalized[s],
        }
        for s in SDGS
    ]
    metrics = {
        "retained_mentions": sum(r["retained_mentions"] for r in sdg_rows),
        "financial_items": len(items),
        "eligible_rows": len(eligible_amounts),
        "eligible_unique_amount_eur": math.fsum(eligible_amounts),
        "tagged_exposure_total_eur": total_finance,
        "narrative_centrality_total": total_narrative,
        "M": mismatch,
        "AS": 1 - mismatch / 85,
        "silent": silent,
        "normalized_L1": None if silent else normalized_l1,
        "normalized_alignment": None if silent else 1 - normalized_l1 / 10,
    }
    return metrics, sdg_rows


def _mean(values):
    values = [v for v in values if v is not None]
    return math.fsum(values) / len(values) if values else None


def _pearson(rows: list[dict[str, Any]], field: str = "AS"):
    pairs = [(r[field], r["retained_mentions"]) for r in rows if r[field] is not None and not r["silent"]]
    if len(pairs) < 2:
        return None
    xs, ys = zip(*pairs)
    mx, my = _mean(xs), _mean(ys)
    xx = math.fsum((x - mx) ** 2 for x in xs)
    yy = math.fsum((y - my) ** 2 for y in ys)
    if not xx or not yy:
        return None
    return math.fsum((x - mx) * (y - my) for x, y in pairs) / math.sqrt(xx * yy)


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    active = [r for r in rows if not r["silent"]]
    return {
        "banks": len(rows),
        "non_silent_banks": len(active),
        "silent_banks": len(rows) - len(active),
        "retained_mentions": sum(r["retained_mentions"] for r in rows),
        "financial_items": sum(r["financial_items"] for r in rows),
        "eligible_rows": sum(r["eligible_rows"] for r in rows),
        "eligible_unique_amount_eur": math.fsum(r["eligible_unique_amount_eur"] for r in rows),
        "tagged_exposure_total_eur": math.fsum(r["tagged_exposure_total_eur"] for r in rows),
        "mean_M_all": _mean(r["M"] for r in rows),
        "mean_AS_all": _mean(r["AS"] for r in rows),
        "mean_AS_non_silent": _mean(r["AS"] for r in active),
        "pearson_AS_retained_mentions_non_silent": _pearson(rows),
        "pearson_n": sum(r["AS"] is not None for r in active),
    }


def _pooled_summary(rows):
    result = _aggregate(rows)
    for old, new in (
        ("banks", "bank_years"),
        ("non_silent_banks", "non_silent_bank_years"),
        ("silent_banks", "silent_bank_years"),
    ):
        result[new] = result.pop(old)
    result["distinct_manifest_banks"] = len({(r["country"], r["bank"]) for r in rows})
    return result


def _audit(record: BankYear, primary_data=None) -> list[dict[str, Any]]:
    output = []
    for section, index, row in _finance_rows(record.corrected):
        effective = (primary_data or record.corrected)["investments"][section][index]
        reasons = []
        if row["construct_type"] == "credit_limit_undrawn":
            reasons.append("strict_primary_excludes_credit_limit_undrawn")
        if not row["score_eligible"]:
            reasons.append("cached_score_eligible_false")
        if row["inclusion_policy"] != "linked_scored":
            reasons.append("cached_inclusion_policy:" + row["inclusion_policy"])
        output.append(
            {
                **record.identity(),
                "source_checkpoint": record.source_checkpoint,
                "section": section,
                "index": index,
                "amount_eur": row["amount_eur"],
                "evidence": row.get("evidence", ""),
                "page_numbers": row.get("page_numbers", []),
                "relevant_sdgs": row["relevant_sdgs"],
                "construct_type": row["construct_type"],
                "original_score_eligible": row["score_eligible"],
                "original_inclusion_policy": row["inclusion_policy"],
                "original_exclusion_reason": row.get("exclusion_reason", ""),
                "legacy_eligible": _legacy_eligible(row),
                "primary_eligible": _eligible(effective),
                "approved_amount_eur": effective["amount_eur"] if _eligible(effective) else 0.0,
                "approved_relevant_sdgs": effective["relevant_sdgs"],
                "source_adjudication_reason": effective.get("adjudication_reason", "not_in_positive_claim_review"),
                "impacted_by_strict_undrawn_exclusion": _legacy_eligible(row) and not _eligible(row),
                "primary_exclusion_reason": effective.get("adjudication_reason", ";".join(reasons))
                if not _eligible(effective)
                else "",
                "credit_limit_evidence_requires_separate_adjudication": bool(
                    CREDIT_LIMIT_TEXT.search(row.get("evidence", ""))
                    and row["construct_type"] != "credit_limit_undrawn"
                ),
            }
        )
    return output


def _profiles(
    sdg_rows: list[dict[str, Any]],
    bank_rows: list[dict[str, Any]],
    *,
    pooled: bool = False,
    undefined_missing_finance: bool = False,
):
    keys = ("country",) if pooled else ("country", "year")
    groups, totals = defaultdict(list), defaultdict(list)
    for row in sdg_rows:
        groups[tuple(row[k] for k in keys)].append(row)
    for row in bank_rows:
        totals[tuple(row[k] for k in keys)].append(row["eligible_unique_amount_eur"])
    output = []
    for group, rows in sorted(groups.items()):
        n = {s: math.fsum(r["narrative_weight"] for r in rows if r["sdg"] == s) for s in SDGS}
        f = {s: math.fsum(r["A_eur"] for r in rows if r["sdg"] == s) for s in SDGS}
        nt, ft = math.fsum(n.values()), math.fsum(f.values())
        for s in SDGS:
            ns, fs = n[s] / nt if nt else 0.0, f[s] / ft if ft else 0.0
            output.append(
                {
                    **dict(zip(keys, group)),
                    "sdg": s,
                    "narrative_weight": n[s],
                    "finance_eur": f[s],
                    "finance_eur_basis": "tagged_exposure_not_conserved_money",
                    "narrative_share": ns,
                    "finance_share": None if undefined_missing_finance and not ft else fs,
                    "gap_pp": None if undefined_missing_finance and (not ft or not nt) else (ns - fs) * 100,
                    "normalized_allocated_eur_for_display": math.fsum(totals[group]) * fs,
                    "display_allocation_basis": "unique_row_amount_times_tagged_share_not_observed_sdg_money",
                }
            )
    return output


def _validate_history(root: Path, country_rows, historical_profiles, historical_pooled):
    references = _read_json(root / TOTALS_PATH)
    expected = {r["stem"]: r for r in references}
    stems = {f"{c}_{y}" for c in COUNTRIES for y in YEARS}
    if len(expected) != len(references) or set(expected) != stems:
        raise ValueError("Historical before_after_totals.json has missing or duplicate country-years")
    checked_totals = 0
    for row in country_rows:
        stem = f"{row['country']}_{row['year']}"
        for phase, prefix in (("before", "historical_raw"), ("after", "corrected_historical")):
            reference = expected[stem][phase]
            checks = {
                "linked_total": (row[f"{prefix}_eligible_unique_amount_eur"], 0.0051),
                "score_eligible_rows": (row[f"{prefix}_eligible_rows"], 0),
                "finance_rows": (row[f"{prefix}_financial_items"], 0),
                "banks": (row["banks"], 0),
            }
            for field, (actual, tolerance) in checks.items():
                if abs(actual - reference[field]) > tolerance:
                    raise ValueError(
                        f"Historical totals mismatch {stem}/{phase}/{field}: "
                        f"computed={actual}, reference={reference[field]}"
                    )
                checked_totals += 1
    profile_checks = []
    for filename, computed, keys in (
        ("sdg_profiles_by_country_year.csv", historical_profiles, ("country", "year", "sdg")),
        ("sdg_profiles_pooled_2019_2024.csv", historical_pooled, ("country", "sdg")),
    ):
        rows = _read_csv(root / PROFILE_PATH / filename)
        reference = {tuple(str(r[k]) for k in keys): r for r in rows}
        actuals = {tuple(str(r[k]) for k in keys): r for r in computed}
        if len(reference) != len(rows) or set(reference) != set(actuals):
            raise ValueError(f"Historical profile coverage mismatch: {filename}")
        max_errors = {}
        for field, tolerance in (
            ("narrative_weight", 0.000051),
            ("finance_eur", 0.0051),
            ("narrative_share", 0.000000501),
            ("finance_share", 0.000000501),
            ("gap_pp", 0.050001),
        ):
            errors = [abs(actuals[k][field] - float(reference[k][field])) for k in reference]
            max_errors[field] = max(errors, default=0.0)
            if max_errors[field] > tolerance:
                raise ValueError(
                    f"Historical Figure 5 profile mismatch: {filename}/{field}: "
                    f"maximum difference {max_errors[field]} exceeds rounding {tolerance}"
                )
        profile_checks.append(
            {
                "source": (PROFILE_PATH / filename).as_posix(),
                "rows": len(rows),
                "max_absolute_errors": max_errors,
                "passed": True,
            }
        )
    return {
        "passed": True,
        "historical_totals_source": TOTALS_PATH.as_posix(),
        "historical_totals_checks": checked_totals,
        "historical_profiles": profile_checks,
    }


def _coverage(records, bank_rows):
    by_bank, score_by_bank = defaultdict(list), defaultdict(list)
    for record in records:
        by_bank[(record.country, record.bank)].append(record)
    for row in bank_rows:
        score_by_bank[(row["country"], row["bank"])].append(row)
    output = []
    for (country, bank), group in sorted(by_bank.items()):
        years = sorted(r.year for r in group)
        output.append(
            {
                "country": country,
                "bank": bank,
                "years_present": years,
                "years_missing": sorted(set(YEARS) - set(years)),
                "bank_years": len(years),
                "source_file_count": sum(len(r.reports) for r in group),
                "complete_2019_2024": years == list(YEARS),
                "complete_and_never_both_zero": years == list(YEARS)
                and all(not r["silent"] for r in score_by_bank[(country, bank)]),
                "identity_note": "Exact manifest identity; Alisa/Evli/Fellow predecessor-labelled report names "
                "are retained without merging."
                if bank in {"Alisa Pankki", "Evli Pankki", "Fellow Pankki"}
                else "Exact manifest identity; no entity resolution applied.",
            }
        )
    return output


def _panels(bank_rows, coverage):
    complete = {(r["country"], r["bank"]) for r in coverage if r["complete_2019_2024"]}
    never_silent = {(r["country"], r["bank"]) for r in coverage if r["complete_and_never_both_zero"]}
    observations, summaries = [], []
    for name, identities, drop_silent in (
        ("complete_including_both_zero", complete, False),
        ("complete_excluding_both_zero_observations", complete, True),
        ("complete_never_both_zero_banks", never_silent, False),
    ):
        members = [
            r for r in bank_rows if (r["country"], r["bank"]) in identities and not (drop_silent and r["silent"])
        ]
        observations.extend({"panel": name, **r} for r in members)
        for country in COUNTRIES:
            for year in YEARS:
                group = [r for r in members if r["country"] == country and r["year"] == year]
                summaries.append(
                    {
                        "panel": name,
                        "country": country,
                        "year": year,
                        "enrolled_complete_banks": sum(c == country for c, _ in identities),
                        "both_zero_observations_excluded": drop_silent,
                        "balanced_panel_guaranteed": not drop_silent,
                        **_aggregate(group),
                    }
                )
    return observations, summaries


def _sensitivities(records, primary_overrides=None):
    observations, summaries = [], []
    for variant, strict, fractional, threshold, normalized in (
        ("primary", True, False, 3, False),
        ("legacy_inclusion", False, False, 3, False),
        ("fractional_sdg_allocation", True, True, 3, False),
        ("threshold_ge_2", True, False, 2, False),
        ("no_threshold_ge_1", True, False, 1, False),
        ("symmetric_normalized_alignment", True, False, 3, True),
    ):
        group_rows = []
        metadata = {
            "variant": variant,
            "priority_threshold": threshold,
            "inclusion": "strict_primary" if strict else "cached_legacy",
            "allocation": "fractional_per_distinct_tag" if fractional else "full_per_distinct_tag",
            "score_scale": "symmetric_normalized_L1_over_10" if normalized else "AS_M_over_85",
        }
        for record in records:
            data = (
                (primary_overrides or {}).get(record.source_checkpoint, record.corrected)
                if strict
                else record.corrected
            )
            metrics, _ = _analyze(data, strict=strict, fractional=fractional, threshold=threshold)
            if normalized:
                metrics["M"] = metrics["AS"] = None
            else:
                metrics["normalized_L1"] = metrics["normalized_alignment"] = None
            group_rows.append({**metadata, **record.identity(), **metrics})
        observations.extend(group_rows)
        for country in COUNTRIES:
            for year in YEARS:
                rows = [r for r in group_rows if r["country"] == country and r["year"] == year]
                summaries.append(
                    {
                        **metadata,
                        "country": country,
                        "year": year,
                        **_aggregate(rows),
                        "mean_normalized_alignment_defined": _mean(r["normalized_alignment"] for r in rows),
                        "normalized_alignment_defined_banks": sum(r["normalized_alignment"] is not None for r in rows),
                    }
                )
    return observations, summaries


def _write_csv(path: Path, rows, fields=None):
    if fields is None:
        fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()}
            )


def _display(row):
    output = {}
    for key, value in row.items():
        if isinstance(value, float):
            value = round(value, 2 if key.endswith("_eur") else 4)
        output[key] = value
    if "M" in row and row["M"] is not None:
        output["AS"] = round(max(0.0, 1 - round(row["M"], 4) / 85), 4)
    return output


def run(repo_root: Path, output_dir: Path, *, primary_overrides=None, excluded_bank_years=None) -> dict:
    """Write portable CSV/JSON artifacts and return a compact, JSON-safe summary.

    Missing inputs, duplicate bank-years, or historical validation failures are
    hard errors. All inputs are loaded and validated before artifact files open.
    Output must not be inside a canonical input directory.
    """
    root, output = Path(repo_root).resolve(), Path(output_dir).resolve()
    for protected in (root / RUN_PATH, root / MANIFEST_PATH, root / TOTALS_PATH.parent, root / PROFILE_PATH):
        if output == protected or protected in output.parents:
            raise ValueError(f"Output directory must not overwrite historical input trees: {output}")
    output.mkdir(parents=True, exist_ok=True)
    records, inputs = _load_inputs(root)
    excluded_bank_years = excluded_bank_years or set()
    canonical_count = len(records)
    canonical_sources = sum(len(r.reports) for r in records)
    bank_rows, sdg_rows, historical_banks, historical_sdgs, audit, manifest_rows = [], [], [], [], [], []
    for record in records:
        primary_data = (primary_overrides or {}).get(record.source_checkpoint, record.corrected)
        primary, sdgs = _analyze(primary_data)
        legacy, legacy_sdgs = _analyze(record.corrected, strict=False)
        raw, _ = _analyze(record.raw, strict=False)
        # Normalized alignment belongs only in its separately labelled sensitivity tables.
        primary.pop("normalized_L1")
        primary.pop("normalized_alignment")
        bank_rows.append(
            {
                **record.identity(),
                "source_checkpoint": record.source_checkpoint,
                "raw_checkpoint": record.raw_checkpoint,
                "source_file_count": len(record.reports),
                **primary,
                "raw_financial_items": raw["financial_items"],
                "historical_raw_eligible_unique_amount_eur": raw["eligible_unique_amount_eur"],
                "historical_raw_eligible_rows": raw["eligible_rows"],
                "corrected_historical_eligible_unique_amount_eur": legacy["eligible_unique_amount_eur"],
                "corrected_historical_eligible_rows": legacy["eligible_rows"],
            }
        )
        historical_banks.append({**record.identity(), **legacy})
        sdg_rows.extend({**record.identity(), "source_checkpoint": record.source_checkpoint, **r} for r in sdgs)
        historical_sdgs.extend({**record.identity(), **r} for r in legacy_sdgs)
        audit.extend(_audit(record, primary_data))
        manifest_rows.append(
            {
                **record.identity(),
                "manifest": record.manifest,
                "source_checkpoint": record.source_checkpoint,
                "checkpoint_bank_identifier": record.corrected["bank"],
                "included_in_primary": (record.country, record.year, record.bank) not in excluded_bank_years,
                "source_file_count": len(record.reports),
                "report_paths": [r["path"] for r in record.reports],
                "report_types": [r["report_type"] for r in record.reports],
                "source_basenames": [Path(r["path"]).name for r in record.reports],
            }
        )
    country_rows = []
    for country in COUNTRIES:
        for year in YEARS:
            rows = [r for r in bank_rows if r["country"] == country and r["year"] == year]
            country_rows.append(
                {
                    "country": country,
                    "year": year,
                    **_aggregate(rows),
                    "source_file_count": sum(r["source_file_count"] for r in rows),
                    "historical_raw_financial_items": sum(r["raw_financial_items"] for r in rows),
                    "corrected_historical_financial_items": sum(r["financial_items"] for r in rows),
                    **{
                        f"{prefix}_{field}": math.fsum(r[f"{prefix}_{field}"] for r in rows)
                        if field.endswith("_eur")
                        else sum(r[f"{prefix}_{field}"] for r in rows)
                        for prefix in ("historical_raw", "corrected_historical")
                        for field in ("eligible_unique_amount_eur", "eligible_rows")
                    },
                    "strict_primary_eligible_unique_amount_eur": math.fsum(
                        r["eligible_unique_amount_eur"] for r in rows
                    ),
                    "strict_primary_eligible_rows": sum(r["eligible_rows"] for r in rows),
                }
            )
    historical_profiles = _profiles(historical_sdgs, historical_banks)
    historical_pooled = _profiles(historical_sdgs, historical_banks, pooled=True)
    validation = _validate_history(root, country_rows, historical_profiles, historical_pooled)
    canonical_country_rows = country_rows

    def included(r):
        return (r["country"], r["year"], r["bank"]) not in excluded_bank_years

    bank_rows = [r for r in bank_rows if included(r)]
    sdg_rows = [r for r in sdg_rows if included(r)]
    records = [r for r in records if (r.country, r.year, r.bank) not in excluded_bank_years]
    country_rows = []
    for historical in canonical_country_rows:
        rows = [r for r in bank_rows if r["country"] == historical["country"] and r["year"] == historical["year"]]
        country_rows.append(
            {
                **historical,
                **_aggregate(rows),
                "canonical_banks_before_source_audit": historical["banks"],
                "source_file_count": sum(r["source_file_count"] for r in rows),
                "strict_primary_eligible_unique_amount_eur": math.fsum(r["eligible_unique_amount_eur"] for r in rows),
                "strict_primary_eligible_rows": sum(r["eligible_rows"] for r in rows),
            }
        )
    profiles = _profiles(sdg_rows, bank_rows, undefined_missing_finance=primary_overrides is not None)
    inputs.extend(
        (
            TOTALS_PATH.as_posix(),
            (PROFILE_PATH / "sdg_profiles_by_country_year.csv").as_posix(),
            (PROFILE_PATH / "sdg_profiles_pooled_2019_2024.csv").as_posix(),
        )
    )
    provenance = [{"path": p, "sha256": hashlib.sha256((root / p).read_bytes()).hexdigest()} for p in sorted(inputs)]
    coverage = _coverage(records, bank_rows)
    panel_banks, panel_countries = _panels(bank_rows, coverage)
    sensitivity_banks, sensitivity_countries = _sensitivities(records, primary_overrides)
    undrawn = [r for r in audit if r["construct_type"] == "credit_limit_undrawn"]
    impacted = [r for r in undrawn if r["impacted_by_strict_undrawn_exclusion"]]
    credit_review = [r for r in audit if r["credit_limit_evidence_requires_separate_adjudication"]]
    tables = {
        "bank_year.csv": bank_rows,
        "bank_year_manuscript_display.csv": [_display(r) for r in bank_rows],
        "bank_sdg.csv": sdg_rows,
        "country_year.csv": country_rows,
        "country_year_manuscript_display.csv": [_display(r) for r in country_rows],
        "country_year_sdg_profiles.csv": profiles,
        "country_sdg_profiles_pooled_2019_2024.csv": _profiles(
            sdg_rows, bank_rows, pooled=True, undefined_missing_finance=primary_overrides is not None
        ),
        "historical_country_year_sdg_profiles.csv": historical_profiles,
        "historical_country_sdg_profiles_pooled_2019_2024.csv": historical_pooled,
        "eligibility_audit.csv": audit,
        "undrawn_rows.csv": undrawn,
        "undrawn_impacted_rows.csv": impacted,
        "credit_limit_evidence_review.csv": credit_review,
        "manifest_coverage.csv": manifest_rows,
        "bank_coverage.csv": coverage,
        "matched_panel_bank_year.csv": panel_banks,
        "matched_panel_country_year.csv": panel_countries,
        "sensitivity_bank_year.csv": sensitivity_banks,
        "sensitivity_country_year.csv": sensitivity_countries,
        "input_provenance.csv": provenance,
    }
    summary = {
        "bank_years": len(bank_rows),
        "canonical_bank_years_before_source_audit": canonical_count,
        "canonical_source_entries_before_source_audit": canonical_sources,
        "source_audited_primary": primary_overrides is not None,
        "excluded_bank_years": [list(k) for k in sorted(excluded_bank_years)],
        "source_file_count": sum(r["source_file_count"] for r in bank_rows),
        "original_153_score_rows_outdated": len(bank_rows) != 153,
        "historical_raw_eligible_unique_amount_eur": math.fsum(
            r["historical_raw_eligible_unique_amount_eur"] for r in canonical_country_rows
        ),
        "corrected_historical_eligible_unique_amount_eur": math.fsum(
            r["corrected_historical_eligible_unique_amount_eur"] for r in canonical_country_rows
        ),
        "primary": _pooled_summary(bank_rows),
        "by_country": {c: _pooled_summary([r for r in bank_rows if r["country"] == c]) for c in COUNTRIES},
        "undrawn_rows": len(undrawn),
        "strict_undrawn_impacted_rows": len(impacted),
        "strict_undrawn_removed_unique_eur": math.fsum(r["amount_eur"] for r in impacted),
        "eligible_credit_limit_evidence_rows_preserved": [
            {k: r[k] for k in ("country", "year", "bank", "section", "index", "amount_eur", "construct_type")}
            for r in credit_review
            if r["primary_eligible"]
        ],
        "complete_panel_banks": {
            c: [r["bank"] for r in coverage if r["country"] == c and r["complete_2019_2024"]] for c in COUNTRIES
        },
        "country_year_bank_counts": {f"{r['country']}_{r['year']}": r["banks"] for r in country_rows},
        "finland_predecessor_manifest_identities": {
            r["bank"]: r["years_present"]
            for r in coverage
            if r["country"] == "finland" and r["bank"] in {"Alisa Pankki", "Evli Pankki", "Fellow Pankki"}
        },
        "zero_finance_country_years": [
            f"{r['country']}_{r['year']}" for r in country_rows if not r["eligible_unique_amount_eur"]
        ],
        "manuscript_discrepancies": [
            f"Canonical checkpoints contain {canonical_count} exact-identity bank-years; "
            f"the primary source-audited subset contains {len(bank_rows)}. The original "
            "153-row workbook-derived score panel is superseded, not a validation target.",
            "Finland has 12 manifest banks in 2020-2022 and 11 in 2023-2024 (6 in 2019). "
            "Fellow remains a separate label through 2022 and is absent in 2023-2024; Alisa appears from 2021 "
            "and Evli through 2021. The 12-to-11 change is coverage, not permission to consolidate predecessors. "
            "Inspect manifest_coverage.csv report names.",
            f"Canonical manifests contain {canonical_sources} source report entries; "
            "the status document's 184 staged files is not the analyzed source-file denominator.",
            "The cached-construct-only exclusion is insufficient. The main driver requires finance and tag "
            "adjudications; credit-limit wording is resolved through source decisions, not a verb override.",
            "Silent AS=1 is mechanical and must not be described as demonstrated narrative-finance alignment.",
            "The prior score-withholding statement is superseded by this deterministic recomputation. "
            "Historical Figure 5 composition is validated separately from bank-year M/AS.",
            "Tagged finance exposures can exceed unique row money; normalized display allocations are synthetic. "
            "Primary AS and symmetric normalized alignment use different scales and must not be compared as levels.",
        ],
        "validation_passed": validation["passed"],
        "artifacts": sorted([*tables, "definitions.json", "validation.json", "summary.json"]),
    }
    input_inodes = set()
    for relative_path in inputs:
        stat = (root / relative_path).stat()
        input_inodes.add((stat.st_dev, stat.st_ino))
    for filename in summary["artifacts"]:
        destination = output / filename
        if destination.is_symlink():
            raise ValueError(f"Output artifact must not be a symlink: {destination}")
        if destination.exists():
            stat = destination.stat()
            if not destination.is_file() or (stat.st_dev, stat.st_ino) in input_inodes:
                raise ValueError(f"Output artifact aliases a historical input or is not a file: {destination}")
    # Empty audit/panel subsets still have headers, so downstream readers remain deterministic.
    for filename, rows in tables.items():
        fields = (
            list(AUDIT_FIELDS)
            if filename
            in {
                "eligibility_audit.csv",
                "undrawn_rows.csv",
                "undrawn_impacted_rows.csv",
                "credit_limit_evidence_review.csv",
            }
            else None
        )
        if not rows and fields is None:
            fields = (
                ["panel", *bank_rows[0]] if filename == "matched_panel_bank_year.csv" else ["country", "year", "bank"]
            )
        _write_csv(output / filename, rows, fields)
    definitions = dict(DEFINITIONS)
    if primary_overrides is not None:
        definitions["primary_eligibility"] = (
            "Source-adjudicated bank-owned current-year payments; approved amounts and SDG tags override "
            "copies of cached rows. Confirmed source-period mismatches are excluded at bank-year level."
        )
    for filename, obj in (
        ("definitions.json", definitions),
        ("validation.json", validation),
        ("summary.json", summary),
    ):
        (output / filename).write_text(
            json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    return summary
