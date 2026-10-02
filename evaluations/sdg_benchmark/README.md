# SDG Extractor Benchmark

Validates the **production** Honesty Scorer SDG-mention classifier
(`honesty_scorer.client.AIClient.fetch_sdg_mentions()`, the exact code path
`honesty_scorer/pipeline.py` calls on real bank-report pages) against the
public [SDG Classification Benchmark](https://github.com/SDGClassification/benchmark)
and the official JRC SDG Mapper baseline.

**Current harness: `run_honesty_classifier_sdg_benchmark.py`.** This calls the
live `SDG_MENTIONS_SYSTEM_PROMPT` / `SDG_MENTIONS_USER_TEMPLATE` from
`honesty_scorer/constants.py` through `AIClient`, and validates responses
through `honesty_scorer.models.normalize_sdg_mentions()` /
`SdgMentionRecord` — the same validation every real classification run uses.
The run-config hash embedded in each cached prediction is derived from the
live prompt/schema/model, so any future change to the production SDG-mention
prompt automatically invalidates the cache and forces a fresh benchmark run.

**Superseded/removed materials (2026-07-02):** the 2026-05-04 legacy
bespoke-prompt harness/results (`legacy_bespoke_prompt_20260504/`) and the
2026-07-01 `bank_report`-framed full-benchmark run and framing-ablation
diagnostic (`../sdg_benchmark_verification_fusion_20260701/`) have been
deleted from the repo. Both were explicitly flagged as not citable: the
legacy harness validated a prompt/schema the pipeline never ran, and the
`bank_report` framing is a domain-mismatch confound on this benchmark's
generic UN/policy text (see "Domain framing" below). Their findings —
that framing suppresses recall on non-bank-report text — are preserved in
this README and in `honesty_scorer/constants.py`; the only citable full-benchmark
number going forward is the `--framing generic` run below.

## Files

- `run_honesty_classifier_sdg_benchmark.py`: current harness, calls the
  production classifier.
- `benchmark.csv`: SDG Classification Benchmark data (1,251 expert-labelled
  text-SDG rows, all 17 SDGs).
- `sdg_mapper_results.csv` / `sdg_mapper_stats.csv`: official JRC SDG Mapper
  benchmark predictions/stats (baseline, unchanged).
- `gpt_oss_120b_generic_predictions.jsonl`: cached production-classifier
  predictions under `--framing generic`, keyed by a framing-aware run-config
  hash.
- `gpt_oss_120b_generic_results.csv`: row-level comparison (classifier vs
  JRC) for the full benchmark under `--framing generic`.
- `gpt_oss_120b_vs_jrc_generic_metrics.json`: full metrics for the full
  benchmark under `--framing generic` — **this is the citable number set for
  the paper.**

## Running it

```bash
source .venv/bin/activate
python3 evaluations/sdg_benchmark/run_honesty_classifier_sdg_benchmark.py --workers 10
```

`--sample-size N --seed S` runs a random N-row pilot instead of the full
1,251-row benchmark (useful for quick smoke tests before a full run).
Predictions are cached in `gpt_oss_120b_predictions.jsonl` keyed by the
run-config hash, so a rerun with an unchanged prompt/model only calls
OpenRouter for rows not already cached under that hash.

### Domain framing: `--framing {bank_report,generic}`

The production prompt explicitly frames the extraction task as "bank
report(s)" (`honesty_scorer.constants.BANK_REPORT_LABEL`, used to build
`SDG_MENTIONS_SYSTEM_PROMPT`/`SDG_MENTIONS_USER_TEMPLATE`). That framing is
correct for the real pipeline, which only ever runs on actual Finland/Ukraine
bank-year PDFs, but this benchmark's text is generic UN/policy/academic
prose, not bank reports. A 2026-07-01 model-fusion framing-ablation
experiment (stratified 498-row sample, since deleted from the repo after its
finding was folded into this doc and into `honesty_scorer/constants.py`)
found that domain-mismatched "bank report" framing measurably suppresses
recall on this benchmark's non-bank-report text.

- `--framing bank_report` (default): calls the exact production prompt/path
  (`AIClient.fetch_sdg_mentions`) -- keep this for parity checks against the
  literal shipped classifier, but do not cite its numbers as the model's
  general extraction capability, since the framing is a confound here.
- `--framing generic`: uses `SDG_MENTIONS_SYSTEM_PROMPT_GENERIC` /
  `SDG_MENTIONS_USER_TEMPLATE_GENERIC` (same `honesty_scorer.constants`
  module, same `AIClient` call path/temperature/response_format/validation,
  bank-report framing wording removed). Use this framing for numbers cited in
  the paper's benchmark-validation section, since the benchmark text is not
  a bank report.

Each framing writes to separate, non-colliding output files
(`gpt_oss_120b_predictions.jsonl` vs `gpt_oss_120b_generic_predictions.jsonl`,
etc.) and is keyed by a framing-aware run-config hash, so switching
`--framing` never silently mixes predictions from the two prompt variants.

## Sources

- SDG Classification Benchmark: https://github.com/SDGClassification/benchmark
- JRC SDG Mapper: https://knowsdgs.jrc.ec.europa.eu/sdgmapper
- Official benchmark `sdg-mapper` results: https://github.com/SDGClassification/benchmark/tree/main/evaluations/sdg-mapper
