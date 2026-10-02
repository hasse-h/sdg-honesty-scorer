# Current status (2026-07-01) — read this first

This file is the single pointer to what is authoritative right now. If a
document elsewhere in this repo disagrees with this file, **this file wins**
unless it explicitly says otherwise.

## Classifier / extraction pipeline

- **Code status:** production-green. `honesty_scorer/` implements a
  fail-closed extraction schema (every financial row must carry
  `source_amount_text`, `source_value`, `source_unit`, `source_currency`,
  `construct_type`, `sdg_support`, `inclusion_policy`; unsupported/unknown
  rows are rejected rather than silently scored), per-report-year FX
  conversion (`YEARLY_FX_TO_EUR` in `honesty_scorer/validation.py`, ECB/NBU
  year-end reference rates 2019-2024), and the extended construct-type
  taxonomy documented in Appendix M (see below).
- **Tests:** `python3 -m unittest discover -s tests -v` — 39 tests pass.
  Lint/format: `python3 -m ruff check .` / `python3 -m ruff format --check .`.
- **Bank-report source files:** all 184 PDFs/XLSX/HTML committed to this
  repo under Git LFS at `data/bank_reports/reports/` (`data/bank_reports/
  .gitattributes` tracks `*.pdf`, `*.xlsx`, `*.html`, `archives/*.zip`).
  Manifests driving the classification runs are at
  `data/bank_reports/manifests/bank_reports_<country>_<year>.csv`.

## Classification runs (all 12 Finland + Ukraine 2019-2024 country-years)

- **Status:** all 12 completed. Workbooks and checkpoints live under
  `evaluations/reruns/country_year_classification_20260630_211343/<stem>/`:
  - `sdg_analysis_<stem>.xlsx` — the raw completed extraction (pre-correction).
  - `sdg_analysis_<stem>_corrected.xlsx` — **the authoritative workbook**,
    after applying the corrections below. Rebuilt from `checkpoints_corrected/`
    via `--resume` with **zero new model API calls**.
- **Runner:** `evaluations/reruns/run_country_year_classifications.py`.
- **Correction script:** `evaluations/reruns/apply_approved_corrections.py`
  (idempotent; `--validate-only` checks every reclassification rule against
  the real extracted evidence text before applying anything).
- **Audit script:** `evaluations/reruns/audit_corrected_totals.py` — 0
  deterministic issues on the corrected checkpoints.

## Corrections applied (in order)

1. **Fusion accuracy review, Finland 2019-2023**
   (`evaluations/fusion_accuracy_completed_20260701_091617/`) and
   **Finland 2024 + Ukraine 2019-2024**
   (`evaluations/fusion_accuracy_new_years_20260701/`) — model-fusion panel
   (Opus 4.8 + GPT-5.5 + Gemini 3.1 Pro) found duplicate extractions,
   facilitated/forward/stock-vs-flow/liability-side misclassifications
   beyond the original 18-row extreme-amount audit.
2. **Three binding methodology decisions (Hasse, 2026-07-01):**
   philanthropy is in scope; non-EUR amounts convert at the report's own
   year-end FX rate; exact-duplicate extraction clusters are auto-collapsed
   mechanically. See Appendix M below for full specification.
3. **Second fusion panel adjudication**
   (`evaluations/fusion_open_items_adjudication_20260701/`) — resolved the
   remaining classification questions into four deterministic
   `construct_type` values now implemented in `honesty_scorer/validation.py`:
   `facilitated_on_behalf_of_customers`, `credit_limit_undrawn` (with the
   financing-verb-governs exception), `forward_commitment`,
   `recipient_side_financing`.
4. **Applied to all 12 checkpoints** — 20 evidence-guarded row
   reclassifications + 16 mechanically auto-collapsed duplicate rows.
   Full audit trail: `evaluations/fusion_open_items_adjudication_20260701/
   correction_audit_log.json`.

**Full methodology write-up (rule/reason/taxonomy-bucket/limitation for
every decision above):**
`evaluations/paper_update_fusion_20260701/appendix_m_methodology_decisions.md`

## Corrected disclosed SDG-linked finance totals (this version's results)

Recomputed from `evaluations/fusion_open_items_adjudication_20260701/
before_after_totals.json`:

| Country | Year | linked_total BEFORE (EUR) | linked_total AFTER (EUR) | score-eligible rows |
|---|---|---|---|---|
| Finland | 2019 | 0.00 | 0.00 | 0→0 |
| Finland | 2020 | 1,316,300,000.00 | 1,320,005,000.00 | 4→4 |
| Finland | 2021 | 26,184,000,000.00 | 43,934,000.00 | 6→3 |
| Finland | 2022 | 3,081,350,000.00 | 2,581,486,500.00 | 6→5 |
| Finland | 2023 | 30,919,338,000.00 | 6,355,342,260.00 | 18→9 |
| Finland | 2024 | 13,821,004,250.00 | 4,723,667,980.00 | 7→5 |
| Ukraine | 2019 | 80,000,000.00 | 0.00 | 1→0 |
| Ukraine | 2020 | 174,800,000.00 | 174,800,000.00 | 2→2 |
| Ukraine | 2021 | 1,346,943,413.08 | 176,358,499.13 | 7→3 |
| Ukraine | 2022 | 125,545,561.77 | 44,770.38 | 3→1 |
| Ukraine | 2023 | 72,064,896.00 | 71,134,057.76 | 3→3 |
| Ukraine | 2024 | 0.00 | 0.00 | 0→0 |
| **Total** | all | **77,121,346,120.85** | **15,446,773,067.27** | — |

**Ukraine 2019, Ukraine 2024, and Finland 2019 have zero score-eligible
disclosed SDG-linked finance after correction.** This is a verified result
of the audited classification chain, not a data gap — state it explicitly
if citing this table, do not present it as a silent zero.

## Paper status

- **Authoritative replacement text for Sections 3.5 (closing) and Section 4:**
  `evaluations/google_doc_update/sections_3_2_to_4_4_replacement_corrected_20260701.txt`
  — includes the corrected totals table above (Table 3), explicit statement
  of the three zero-finance bank-years, narrowed withholding rationale for
  the SDG Honesty Score (H_by), and a confidence/verification-needs section.
- **Section 3.3 benchmark numbers (2026-07-02 update):** the full 1,251-row
  SDG Classification Benchmark validation was rerun with `--framing generic`
  (`evaluations/sdg_benchmark/run_honesty_classifier_sdg_benchmark.py
  --framing generic --workers 10`) after the legacy bespoke-prompt harness and
  the `bank_report`-framed run/framing-ablation diagnostic were removed from
  the repo as not citable (domain-mismatch confound — the benchmark text is
  generic UN/policy prose, not an actual bank report; see
  `evaluations/sdg_benchmark/README.md`). The Section 3.3 text and Figures 1-2
  in the authoritative replacement doc above now reflect this generic-framing
  run: Honesty extractor at priority ≥ 3 achieves F1 0.847 (vs JRC 0.721),
  AUPRC 0.895 (vs JRC 0.749), paired-bootstrap F1 advantage +0.126 (95% CI
  [+0.091, +0.162]). Citable metrics file:
  `evaluations/sdg_benchmark/gpt_oss_120b_vs_jrc_generic_metrics.json`.
- **What is still withheld and why:** the SDG Honesty Score H_by, the
  narrative-finance mismatch statistic M_by, and the SDG-level composition
  of divergence (Section 4.4) all require recombining the corrected
  financial profile with the narrative profile at the individual-SDG-tag
  level (Section 3.4 equations 2-6). That recomputation has not yet been
  rerun against the corrected checkpoints — this is the one remaining step
  before the paper's headline honesty-score results can be finalized.
- **Live Google Doc:** NOT updated. OAuth for programmatic Google Docs
  edits is unavailable in this environment (`invalid_grant`, no way to
  complete the interactive consent flow here). The corrected replacement
  text above is ready to paste in manually, or to push once OAuth is set up
  from an environment that can complete the browser consent flow.
- **Superseded materials:** anything under
  `evaluations/google_doc_update/superseded_pre_finance_audit_20260518/`
  reports honesty-score levels/trajectories computed *before* the financial
  audit and correction work above. Do not cite those figures.

## Full provenance chain (chronological)

1. `evaluations/bank_report_classification_20260630_162957/` — first
   model-fusion validation workflow design (pre-dates the actual reruns).
2. `evaluations/reruns/finance_extraction_20260630_153241/`,
   `finance_extraction_20260630_aktia_retry/`,
   `classifier_runtime_*_20260630_200318/`,
   `recharged_aktia_20260630_210451/` — runtime-hardening debugging history
   (incomplete-JSON retries, timeout handling, checkpointing) before the
   full 12-country-year run succeeded.
3. `evaluations/reruns/country_year_classification_20260630_211343/` — the
   completed run, raw + corrected workbooks (see above).
4. `evaluations/fusion_accuracy_completed_20260701_091617/` (Finland
   2019-2023) and `evaluations/fusion_accuracy_new_years_20260701/`
   (Finland 2024 + Ukraine 2019-2024) — accuracy review fusion panels.
5. `evaluations/fusion_open_items_adjudication_20260701/` — second fusion
   panel resolving open construct-type questions; correction application
   and audit scripts' outputs.
6. `evaluations/paper_update_fusion_20260701/` — methodology note (Appendix
   M) and Section 3.5/4 paper update, produced by a third fusion pass.

## Relevant commits

- `38f8ed2` Use per-report-year FX rates (ECB/NBU year-end) for non-EUR conversion
- `8cc48d3` Add fusion-adjudicated construct types
- `be86a88` Apply approved corrections to all 12 country-year checkpoints; rebuild workbooks
- `08acf70` Model-fusion methodology note + corrected Section 3.5/4 paper update
