# Honesty Scorer Repo Guidance

- **Start here for current results/status:** `evaluations/CURRENT_STATUS.md`
  is the single pointer to what is authoritative — corrected classification
  totals, which paper draft is current, and what's still withheld. If any
  other doc disagrees with it, `CURRENT_STATUS.md` wins.
- The documented entrypoint remains `python3 sdg_honesty_scorer.py REPORT1.pdf REPORT2.pdf`, but implementation lives in the `honesty_scorer/` package. Keep `sdg_honesty_scorer.py` as a compatibility wrapper for existing imports and notebooks.
- `AIClient` calls OpenRouter chat completions and expects JSON object responses. Preserve the contracts expected by `fetch_sdg_mentions()` and `categorize_investments()` because tests and downstream workbooks assume those return shapes. `categorize_investments()` takes an optional `report_year` argument (threaded through to per-report-year FX conversion); keep that signature when changing the client.
- OpenRouter routing is only for open-weight/open-access models. Do not route proprietary OpenAI, Claude, or Gemini models through this client; only `openai/gpt-oss*` is allowed from OpenAI on OpenRouter.
- Investment extraction rows must include `page_numbers` and `evidence` in addition to amount, SDGs, and justification. These fields support paper auditability.
- The SDG Honesty Score financial denominator is linked SDG amount only. Unlinked investments are reported separately but do not enter the SDG profile denominator.
- Non-EUR amounts convert using the report's own year-end FX rate (`YEARLY_FX_TO_EUR` in `honesty_scorer/validation.py`, ECB/NBU year-end reference rates keyed 2019-2024), falling back to a fixed rate table (`FIXED_FX_TO_EUR`) only for EUR or years outside that range. Do not reintroduce a single fixed rate for all years — that was the pre-2026-07-01 behavior and it materially distorted multi-year comparisons, especially UAH.
- `construct_type` has four buckets: `SCORABLE_CONSTRUCTS` (scored), `GROSS_CONTEXT_CONSTRUCTS` (retained for audit, excluded from score — includes `facilitated_sustainable_finance`, `facilitated_on_behalf_of_customers`, `gross_aum`, `gross_sustainable_finance`, `portfolio_balance`, `taxonomy_denominator`, `credit_limit_undrawn`), and `EXCLUDED_CONSTRUCTS` (retained for audit, excluded — includes `lending_portfolio_total`, `market_share`, `narrative_only`, `portfolio_share_or_growth`, `target`, `forward_commitment`, `recipient_side_financing`, `unknown`). `credit_limit_undrawn` has a financing-verb-governs exception in `classify_inclusion()`: if the evidence text also contains an explicit financing verb ("were financed", "disbursed", "provided", "granted") attached to a concrete executed agreement, it is treated as scorable instead. See `evaluations/paper_update_fusion_20260701/appendix_m_methodology_decisions.md` for the full rationale behind each bucket.
- `pdfplumber`, `pandas`, and `openpyxl` are optional imports in code but required for real runs. The script can still compile and show `--help` without them, but PDF extraction and Excel export will fail when they are missing.
- Parsed PDF text is cached beside each input as `<report>.parsed.json`. Reruns reuse that cache, so clear it deliberately if you need the script to re-read a changed PDF.
- For exploratory path-based runs, bank grouping comes from the filename prefix before the first `_` or `-`. For paper or audit runs, use `--manifest` with `path`, `bank`, `country`, `year`, and `report_type` columns so bank-years cannot be merged accidentally. Production manifests for the Finland/Ukraine 2019-2024 corpus live at `data/bank_reports/manifests/bank_reports_<country>_<year>.csv`; source PDFs are Git-LFS-tracked under `data/bank_reports/reports/`.
- SDG mention extraction runs in parallel with `ThreadPoolExecutor(max_workers=4)` over page chunks, then investment categorization runs once over the merged full text. Keep those stages aligned if you change batching or concurrency.
- Dependencies are declared in `pyproject.toml`; tests live under `tests/`. Lightweight verification is `python3 -m unittest discover -s tests -v`, `python3 -m py_compile sdg_honesty_scorer.py`, `python3 sdg_honesty_scorer.py --help`, and `python3 -m ruff check .`; full end-to-end runs also need real PDFs and repo-local OpenRouter credentials.
- Do not hardcode user-specific absolute paths. Derive repository paths from `Path(__file__).resolve()` or accept them as CLI arguments.

## Skill-Driven Coding Flow

- This is the default workflow for coding in this repo. Unless a repo-specific rule in this file says otherwise, use this flow whenever you change code, tests, build scripts, CI, or developer tooling.
- In Claude with the installed `addy-agent-skills` plugin, `/spec`, `/plan`, `/build`, `/test`, `/review`, and `/ship` are literal commands.
- In Codex and other agents here, use the closest installed local skill plus the repo's actual commands instead of expecting those slash commands to exist natively.
- Treat the installed local Codex superpower skills as this repo's practical equivalent of the upstream `agent-skills` workflow. The overlap is partial, so map intent to the closest installed skill rather than assuming a one-to-one command clone.
- When a task clearly matches an installed skill, use it by default instead of free-handing the workflow.
- For non-trivial features, refactors, or multi-file changes, default to `plan_and_code`, then implement in small safe slices and verify each slice with the repo commands in this file.
- For large files, logs, JSON, CSV, HTML, or long Markdown, use `large-file-navigation` before trying to read the whole artifact.
- For secrets or env-var changes, use `age-secrets`. Never create or commit a plaintext `.env`; use `.env.age` and in-memory decryption instead.
- For model or provider work, use `provider-routing`. Route GPT models directly through OpenAI, Claude through Anthropic, Gemini through Google or Vertex, and use OpenRouter only for intentional open-weight model usage after checking WhatLLM.
- For `AGENTS.md`, `CLAUDE.md`, and other instruction-oriented Markdown, use `markdown-file-hygiene` so guidance stays concise and content-first.
- For OpenAI API or product questions, use `openai-docs` when available and prefer official documentation over memory.
- Default lifecycle expectation when coding: define the change, plan the smallest safe slice, implement, verify with the repo's own test, lint, build, and run commands, review risks and regressions, then summarize exactly what changed and how it was validated.
- Skills guide the default process; this repo's own commands and constraints remain the source of truth.
