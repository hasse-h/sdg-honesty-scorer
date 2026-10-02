"""Apply source-reviewed decisions to copies; preserve every cached input."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from reproduction import banks


def load(repo: Path) -> tuple[dict, set, dict]:
    """Require complete positive-claim review and exact evidence/amount/tag guards."""
    records, _ = banks._load_inputs(repo)
    by_path = {r.source_checkpoint: r for r in records}
    primary = {p: copy.deepcopy(r.corrected) for p, r in by_path.items()}
    expected = {
        (p, section, index): row
        for p, record in by_path.items()
        for section, index, row in banks._finance_rows(record.corrected)
        if banks._legacy_eligible(row)
    }
    payload = json.loads((repo / "reproduction/finance_adjudications.json").read_text())
    decisions = {}
    for decision in payload["rows"]:
        key = (decision["checkpoint"], decision["section"], decision["row_index"])
        if key in decisions or key not in expected:
            raise ValueError(f"Duplicate or unknown finance adjudication: {key}")
        original = expected[key]
        if (
            original["evidence"] != decision["original_evidence"]
            or original["amount_eur"] != decision["original_amount_eur"]
        ):
            raise ValueError(f"Finance evidence/amount guard failed: {key}")
        if hashlib.sha256((repo / key[0]).read_bytes()).hexdigest() != decision["checkpoint_sha256"]:
            raise ValueError(f"Finance checkpoint hash guard failed: {key}")
        if decision["decision"] not in ("include", "exclude"):
            raise ValueError(f"Unknown finance decision: {key}")
        amount = banks._number(decision["approved_amount_eur"], "adjudicated amount")
        included = decision["decision"] == "include"
        if included != (amount > 0):
            raise ValueError(f"Decision/approved amount conflict: {key}")
        if included and amount != original["amount_eur"] and not decision.get("amount_adjustment"):
            raise ValueError(f"Unexplained amount adjustment: {key}")
        row = primary[key[0]]["investments"][key[1]][key[2]]
        row.update(
            score_eligible=included,
            inclusion_policy="linked_scored" if included else "excluded",
            amount_eur=amount,
            adjudication_reason=decision["reason_code"],
            adjudication_source=decision["source_report"],
            adjudication_pages=decision["source_pages"],
        )
        decisions[key] = decision
    if decisions.keys() != expected.keys():
        raise ValueError("Finance adjudications do not cover exactly all cached positive claims")

    tags = json.loads((repo / "reproduction/finance_tag_adjudications.json").read_text())
    included_keys = {k for k, d in decisions.items() if d["decision"] == "include"}
    seen = set()
    for decision in tags["rows"]:
        key = (decision["checkpoint"], decision["section"], decision["row_index"])
        if key in seen or key not in included_keys:
            raise ValueError(f"Duplicate or unapproved finance tag decision: {key}")
        if expected[key]["relevant_sdgs"] != decision["original_relevant_sdgs"]:
            raise ValueError(f"Original SDG tag guard failed: {key}")
        approved = decision["approved_relevant_sdgs"]
        if not approved or len(set(approved)) != len(approved):
            raise ValueError(f"Empty or duplicated approved tags: {key}")
        for sdg in approved:
            banks._sdg(sdg)
        row = primary[key[0]]["investments"][key[1]][key[2]]
        row["relevant_sdgs"] = approved
        row["tag_adjudication_reason"] = decision["rationale"]
        seen.add(key)
    if seen != included_keys:
        raise ValueError("Every approved payment must have a source-reviewed SDG assignment")

    exclusions = json.loads((repo / "reproduction/bank_year_exclusions.json").read_text())["rows"]
    excluded = {(r["country"].lower(), int(r["year"]), r["bank"]) for r in exclusions}
    identities = {(r.country, r.year, r.bank) for r in records}
    if len(excluded) != len(exclusions) or not excluded.issubset(identities):
        raise ValueError("Duplicate or unknown excluded bank-year")
    return (
        primary,
        excluded,
        {
            "reviewed_positive_claims": len(decisions),
            "approved_positive_claims_before_bank_year_exclusions": len(included_keys),
            "excluded_positive_claims": len(decisions) - len(included_keys),
            "approved_unique_eur_before_bank_year_exclusions": sum(
                d["approved_amount_eur"] for d in decisions.values()
            ),
            "bank_year_exclusions": exclusions,
            "scope": (
                "Source review of cached positive claims, not an exhaustive search for missing disclosures "
                "or external transaction verification."
            ),
        },
    )
