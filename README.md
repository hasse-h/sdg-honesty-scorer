# SDG Honesty Scorer

An evidence-linked workflow for comparing SDG narrative emphasis with disclosed financial records. The repository name is historical: its score does not establish honesty, intent, verified finance or sustainable-development impact.

## Reproduce the manuscript analysis

```bash
uv sync --frozen --extra reproduce --extra dev
uv run --frozen --extra reproduce python -m reproduction
```

Numerical replay is offline and uses frozen classifications, source adjudications and explicit coverage exclusions. No API key, model call or original PDF download is needed. It rebuilds the bank-year statistics, benchmark metrics and confidence intervals, sensitivity analyses, manuscript tables and Figures 1–5.

See [the reproduction guide](reproduction/README.md) for inputs, outputs, definitions and limitations. Earlier workbooks and manuscript drafts are historical audit stages and are not all included in this public archive. In particular, the earlier EUR 15.4 billion harness result is superseded by source review; it must not be presented as verified disbursement.

## What this public archive contains

This repository is the public reproduction package for the manuscript. It includes the analysis code, frozen classification caches, source adjudications, benchmark prediction files, manifests and the lockfile used by `python -m reproduction`.

It does **not** include:

- API keys or the encrypted `.env.age` file kept only in the private working repository
- original bank-report PDFs or other Git LFS report files (those reports keep their publishers' terms; numerical replay does not need them)
- editor OAuth scripts, draft-document backups and run logs from the private working repository

No licence file is included in this archive. Do not assume an open-source licence. Third-party benchmark rows and any short source excerpts in the adjudication files remain under their original terms.

The classification model recorded for the benchmark and bank-report extraction is `openai/gpt-oss-120b` (GPT-OSS 120B) via OpenRouter. Replaying the published numbers does not call that model.

## Optional new extraction

The CLI below extracts report text, calls an OpenRouter-hosted open-weight model and writes evidence-bearing Excel sheets. This is separate from replaying the manuscript analysis. New model predictions require source review and can differ from the frozen study inputs.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e '.[dev,eval]'
```

Optional new extraction needs an OpenRouter API key. This public archive does not contain one. If you run new extraction locally, keep the key in an uncommitted `.env` or in a private `.env.age`, never in git. The only supported key name is:

```text
OPENROUTER_API_KEY
```

Use `age` with `~/.api_keys/age.key` to edit it via a private temporary file. Never commit `.env` or a decrypted copy.

Optional environment variables:

- `OPENROUTER_MODEL` - defaults to `openai/gpt-oss-120b`
- OpenRouter is intentionally limited to open-weight/open-access models. OpenAI model IDs are rejected except `openai/gpt-oss*`; proprietary OpenAI, Claude, and Gemini models must be called through their direct APIs.
- `OPENROUTER_BASE_URL` - defaults to `https://openrouter.ai/api/v1/chat/completions`; must stay on `https://openrouter.ai` unless `OPENROUTER_ALLOW_UNSAFE_BASE_URL=1` is explicitly set for local testing
- `OPENROUTER_SITE_URL` - optional OpenRouter attribution header
- `OPENROUTER_APP_NAME` - defaults to `SDG Honesty Scorer`
- `AGE_BIN` - optional explicit path to the `age` binary

## Usage

For quick exploratory runs:

```bash
python3 sdg_honesty_scorer.py path/to/reports/ Nordea_2024.pdf OP-annual-report.pdf
```

For paper or audit runs, use an explicit manifest so bank-years cannot be merged accidentally:

```csv
path,bank,country,year,report_type
reports/Nordea_2024.pdf,Nordea,Finland,2024,annual
reports/Nordea_sustainability_2024.pdf,Nordea,Finland,2024,sustainability
```

```bash
python3 sdg_honesty_scorer.py --manifest reports_manifest.csv --output sdg_analysis.xlsx
```

Parsed PDF text is cached beside each input as `<report>.parsed.json`. Delete that cache if the PDF changes and you want the script to re-parse it.

## Scoring Contract

The historical scoring implementation compares a 0-5 narrative SDG profile with a 0-5 financial SDG profile using L1 distance. The financial profile denominator is the sum of SDG-linked amounts only. Unlinked investments are reported in the workbook but do not enter the SDG denominator because they cannot be assigned to a specific SDG.

Investment rows enter the SDG profile only when deterministic validation marks them as
`inclusion_policy = linked_scored` and `score_eligible = true`. Rows classified as gross AUM,
facilitated sustainable-finance aggregates (including finance issued/arranged on behalf of
third-party customers), taxonomy denominators, total lending, market-share/portfolio-growth
figures, portfolio balances (year-end stock rather than new-year flow), undrawn credit limits,
narrative targets or forward commitments, financing the reporting bank itself received (e.g. IFI
loans, syndicated loans as borrower rather than lender), or weakly supported SDG associations are
retained for audit as `gross_context_only` or `excluded` but do not affect the score. See
`evaluations/paper_update_fusion_20260701/appendix_m_methodology_decisions.md` for the full
rationale behind each construct-type bucket.

The model is asked to report the source amount exactly as written. Python code, not the model,
performs scale conversion and currency conversion using the report's own year-end FX rate
(`YEARLY_FX_TO_EUR` in `honesty_scorer/validation.py`, ECB/NBU year-end reference rates keyed by
report year 2019-2024, with a fixed-rate fallback for EUR or years outside that range), and
records `conversion_source`; non-EUR conversions are flagged with `needs_fx_review = true`.
Proprietary GPT/Claude/Gemini models must not be routed through OpenRouter; GPT-OSS remains
the default OpenRouter model until a separate direct-provider client is added and tested.

## Development Checks

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile sdg_honesty_scorer.py
python3 sdg_honesty_scorer.py --help
python3 -m ruff check .
```
