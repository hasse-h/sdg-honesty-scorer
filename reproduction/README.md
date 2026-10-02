# Reproduce the SDG screening analysis

With Python 3.11 or newer, install the locked environment from the Honesty_Scorer checkout and replay the saved classifications:

```bash
uv sync --frozen --extra reproduce --extra dev
uv run --frozen --extra reproduce python -m reproduction
uv run --frozen --extra reproduce --extra dev python -m unittest discover -s tests -v
```

The installation downloads Python packages. The reproduction command itself disables network connections and requires no API credentials, model calls, PDF parsing, translations or Git LFS downloads. Use `--output /path/to/results` to select an output directory. Do not write outputs into an input directory.

The committed `uv.lock` resolves supported Python environments. `reproduction/output/reproduction_summary.json` records the Python and numerical-library versions actually used. Analytical CSVs preserve full precision; manuscript tables round explicitly. Matplotlib embeds DejaVu fonts in PDF figures and supplies SVG and 300-dpi PNG companions.

## Inputs and audit stages

See [verification and reviewer archive instructions](VERIFICATION.md) for the fresh-environment checks and commands to export the frozen inputs together with generated tables and figures.

1. The canonical manifests contain 152 cached bank-years and 181 report entries for Finland and Ukraine, 2019–2024. These are exact manifest identities, not an inferred merger history or an asset-weighted population.
2. Raw checkpoints and the earlier `checkpoints_corrected` are frozen historical stages. Their old EUR 77.1 billion and EUR 15.4 billion totals are reproduced and checked against saved references; the latter is **not** the current eligible-finance result.
3. `finance_adjudications.json` reviews all 35 claims retained by the earlier harness. It preserves exact evidence and amount guards, source-report/page references, source hashes, excerpts and decisions. Thirty-three are excluded. The two approved payments total EUR 7,031.77 before bank-year exclusions: Oma Säästöpankki 2024, EUR 6,250; Sense Bank 2023, EUR 781.77 after removing the employee-funded share.
4. `finance_tag_adjudications.json` documents source-supported SDG tags for those payments. It repairs a joined-column error in Oma's original SDG attribution. Full multi-tag exposure is distinct from unique payment money.
5. `bank_year_exclusions.json` quarantines ten bank-years with source-period, duplicate/overlapping-source, mixed-entity or pre-bank population problems from both narrative and finance analysis. No cached narrative is silently reassigned to another year. `source_year_audit.json` and its review provide the corpus checks.
6. `input_checksums.json` freezes the exact analytical files. Missing, added or changed input files cause the main command to fail. `adjudication.py` separately requires complete positive-claim coverage and exact row guards.

The standalone bank module's default is the historical cached-flag calculation, retained for regression testing. **Use `python -m reproduction` for the source-adjudicated manuscript analysis**; its driver always applies finance, tag and bank-year decisions. Neither path changes input checkpoints.

## Outputs

- `output/manuscript_tables.json`: editable cell data for Tables 1–4 and B.1–B.6.
- `output/figures/figure_1` through `figure_5`: PDF, SVG and PNG.
- `output/banks/bank_year.csv`, `country_year.csv`, `bank_sdg.csv`: primary observations and aggregations.
- `output/banks/eligibility_audit.csv`: original versus approved financial treatment. Consult source decisions for payer, period and tag corrections.
- `output/banks/manifest_coverage.csv`, `bank_coverage.csv`: manifest identities and report paths.
- `output/banks/sensitivity_*.csv`: historical inclusion on the same retained bank-year cohort, fractional multi-SDG allocation, priority ≥ 1/2/3, and symmetric normalised-narrative alignment.
- `output/banks/matched_panel_*.csv`: complete exact-identity panels, with distinct silent-case treatments.
- `output/banks/historical_*`, `validation.json`: regression checks for the superseded totals and composition profiles.
- `output/benchmark/`: threshold metrics, exact centrality buckets, missed positives, available model/prompt provenance, and both bootstrap intervals.

## Definitions that affect interpretation

Main narrative emphasis is maximum cached centrality per bank-year-SDG, set to zero below priority 3. Finance adds each approved payment's full amount to every distinct supported SDG. `E = 5A/sum(A)` when finance exists, otherwise zero; `M = sum(abs(R-E))`; `AS = 1-M/85`. Both-zero observations mechanically have AS 1 and are reported separately.

Country-year composition uses `mention_count × retained centrality`, normalised separately from full-tag financial exposure. Its percentage-point gaps **do not decompose bank-year M**. Finance shares and composition gaps are undefined when approved finance is absent. Tagged exposures can exceed unique payment totals; Appendix B reports the former explicitly.

The symmetric sensitivity uses `R_norm=5R/sum(R)` and `1-L1(R_norm,E)/10`. Both-zero observations are undefined; narrative-positive/finance-zero observations mechanically equal 0.5. Its level must not be compared directly with AS. With only two approved payments, main AS predominantly reflects narrative breadth. It is not a measure of verified activity, impact, deceit or national sustainability performance.

## Benchmark and uncertainty

The generic-domain benchmark contains 1,251 text–SDG rows and 1,247 exact text strings. At priority ≥ 3, cached GPT-OSS predictions have micro-F1 0.847176 versus JRC 0.720953 (difference 0.126223). The paired text-cluster bootstrap 95% percentile interval is [0.092109, 0.161923]; the historical row-bootstrap interval is [0.091414, 0.161673]. Both use 10,000 draws, NumPy PCG64, seed 20260504. Exact string equality defines clusters; all rows of a sampled cluster and both models' predictions travel together. Thresholds were explored on this same benchmark. Threshold 2 has higher F1; threshold 3 represents the central-claim specification, not a separately validated optimum.

The benchmark prompt differs from the bank-report prompt. It does not validate financial extraction, bank-report centrality, implicit claims separately, or washing detection. Available run identifiers and prompt/configuration metadata are preserved; unavailable immutable backend snapshots, raw provider-response archives and translation-verification logs are not reconstructed or claimed.

## Source rights and access

[Study repository](https://github.com/hasse-h/sdg-honesty-scorer). This public archive is the deposit cited by the manuscript. Numerical replay does not need credentials.

[External SDG benchmark](https://github.com/SDGClassification/benchmark). Original bank reports and benchmark material retain their original ownership and terms. This package grants no new licence over third-party sources. Original reports are not redistributed here; they are optional for numerical replay and are needed only to independently re-read the source pages. Source hashes and report/page references identify the versions reviewed. This repository does not add a software licence.

These checks reproduce conditional calculations and inspect known positive claims. They do not provide an exhaustive financial-recall audit, independent transaction verification, a validated translation corpus, or independent bank-report narrative labels. Those are research validation needs, not properties supplied by a successful replay.
