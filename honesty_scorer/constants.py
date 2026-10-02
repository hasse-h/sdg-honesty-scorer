"""Constants and prompt templates for SDG honesty extraction."""

DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-oss-120b"
DEFAULT_TIMEOUT_SECONDS = 120.0
DEFAULT_MAX_RETRIES = 3
SAFE_OPENROUTER_HOSTS = {"openrouter.ai"}
DANGEROUS_EXCEL_PREFIXES = ("=", "+", "-", "@")
SDG_NUMBERS = range(1, 18)
MAX_MISMATCH = 85.0
SCORER_VERSION = "0.2.0"

# Named constant for the "bank report" domain-framing wording injected into the
# extraction prompts below. This exists so the bank-report framing is applied
# deliberately, in one place, only when the text actually being extracted is a bank
# report (the real production path in honesty_scorer/pipeline.py, run over the
# Finland/Ukraine bank-year PDFs) -- and can be left OUT for a domain-neutral run (e.g.
# validating the extractor against a general-domain benchmark) without that framing text
# leaking into numbers the paper cites. See SDG_MENTIONS_SYSTEM_PROMPT_GENERIC /
# SDG_MENTIONS_USER_TEMPLATE_GENERIC below for the no-framing counterpart. The
# domain-mismatch finding that motivated this split (bank-report framing measurably
# suppresses recall on non-bank-report text) is documented in
# evaluations/sdg_benchmark/README.md; the citable full-benchmark numbers are in
# evaluations/sdg_benchmark/gpt_oss_120b_vs_jrc_generic_metrics.json.
#
# IMPORTANT: SDG_MENTIONS_SYSTEM_PROMPT / SDG_MENTIONS_USER_TEMPLATE /
# INVESTMENT_USER_TEMPLATE below are built from this constant to be BYTE-IDENTICAL to the
# previous hardcoded prompt text -- they are what produced the completed Finland/Ukraine
# 2019-2024 classification runs (see evaluations/CURRENT_STATUS.md) and are hashed into
# AIClient/benchmark run-config caches (gpt_oss_120b_predictions.jsonl). Do not change
# BANK_REPORT_LABEL's value without re-verifying the rendered prompt strings are
# unchanged, or every cached prediction and downstream cited number invalidates
# silently. Plain `.replace()` on a placeholder token is used (not an f-string) because
# the templates below contain literal JSON braces that an f-string would try to
# interpret as expressions.
BANK_REPORT_LABEL = "bank report"

SDG_MENTIONS_SYSTEM_PROMPT = """You extract Sustainable Development Goal reporting claims from __BANK_REPORT_PLURAL__.
Return only valid JSON. Use the page labels provided in the text when reporting page_numbers.
importance_score is 0-5: 0 means absent, 5 means central to the report section.
Do not invent page numbers, amounts, or SDG claims that are not supported by the supplied text.
""".replace("__BANK_REPORT_PLURAL__", f"{BANK_REPORT_LABEL}s")

SDG_MENTIONS_USER_TEMPLATE = """Analyze this __BANK_REPORT_HYPHEN__ excerpt and return JSON with this exact shape:
{
  "sdg_data": [
    {
      "sdg_number": 1,
      "mention_count": 0,
      "importance_score": 0.0,
      "page_numbers": []
    }
  ]
}

Include SDGs 1 through 17 when they are mentioned or materially discussed. Omit SDGs with no evidence.
Text:
{report_text}
""".replace("__BANK_REPORT_HYPHEN__", BANK_REPORT_LABEL.replace(" ", "-"))

# Domain-neutral counterpart: same instructions, schema, and call path, but with the
# BANK_REPORT_LABEL framing removed. Use this pair -- not the framed pair above -- when
# the text being classified is NOT a bank report (e.g. the public SDG Classification
# Benchmark, which is generic UN/policy/academic prose), so that benchmark numbers cited
# in the paper are not confounded by an irrelevant "bank report" framing instruction.
SDG_MENTIONS_SYSTEM_PROMPT_GENERIC = """You extract Sustainable Development Goal themes from the supplied text.
Return only valid JSON. Use the page labels provided in the text when reporting page_numbers.
importance_score is 0-5: 0 means absent, 5 means central to the text.
Do not invent page numbers or SDG themes that are not supported by the supplied text.
"""

SDG_MENTIONS_USER_TEMPLATE_GENERIC = """Analyze this text excerpt and return JSON with this exact shape:
{
  "sdg_data": [
    {
      "sdg_number": 1,
      "mention_count": 0,
      "importance_score": 0.0,
      "page_numbers": []
    }
  ]
}

Include SDGs 1 through 17 when they are mentioned or materially discussed. Omit SDGs with no evidence.
Text:
{report_text}
"""

INVESTMENT_SYSTEM_PROMPT = """You extract source-grounded bank finance records for later deterministic validation.
Return only valid JSON. Include concise justifications tied to evidence in the supplied text.
Do not convert currencies, infer missing amounts, or treat generic AUM, total lending, taxonomy denominators,
market shares, portfolio growth, or narrative targets as SDG-linked finance.
Report the source amount exactly as written, classify the finance construct, and state how strongly the cited text
supports the SDG tags.
Do not invent investments, SDGs, amounts, page numbers, or evidence text.
"""

INVESTMENT_USER_TEMPLATE = """Analyze this __BANK_REPORT_HYPHEN__ text and return JSON with this exact shape:
{
  "keyword_categories": [
    {
      "category": "Renewable energy",
      "subcategories": ["solar", "wind"],
      "amount_eur": 0.0,
      "source_amount_text": "EUR 300,000 thousand",
      "source_value": 300000,
      "source_unit": "thousand",
      "source_currency": "EUR",
      "construct_type": "disclosed_sdg_linked_finance",
      "sdg_support": "explicit",
      "relevant_sdgs": [7, 13],
      "justification": "Short evidence-based reason.",
      "page_numbers": [12],
      "evidence": "Short quotation tied to the page evidence."
    }
  ],
  "investment_instruments": [
    {
      "instrument": "Green bond",
      "subcategories": ["energy efficiency"],
      "amount_eur": 0.0,
      "source_amount_text": "DKK 365bn",
      "source_value": 365,
      "source_unit": "billion",
      "source_currency": "DKK",
      "construct_type": "disclosed_sdg_linked_finance",
      "sdg_support": "strong",
      "relevant_sdgs": [7, 13],
      "justification": "Short evidence-based reason.",
      "page_numbers": [14],
      "evidence": "Short quotation tied to the page evidence."
    }
  ],
  "unlinked_investments_eur": 0.0
}

Use page labels such as [PAGE 12] for page_numbers. Include evidence for every investment item.

Field rules:
- source_amount_text: exact amount phrase from the supplied text.
- source_value: numeric value as written before scale conversion; for EUR 300,000 thousand use 300000, not 300000000.
- source_unit: one of actual, thousand, million, billion, trillion.
- source_currency: the source currency such as EUR, DKK, UAH, USD. Do not translate it to EUR.
- amount_eur: leave 0.0 unless the source itself states an explicit EUR amount in actual euros; deterministic code
  will recompute this field from source_value, source_unit, and source_currency.
- construct_type: use disclosed_sdg_linked_finance only for concrete finance the reporting bank itself disbursed,
  deployed, or extended this year as SDG-linked/sustainable, to customers or projects (not to itself). Use these
  other constructs when they fit better:
  - facilitated_sustainable_finance / facilitated_on_behalf_of_customers: bank arranged, underwrote, mobilized, or
    issued on behalf of third-party/customer funds (e.g. "issued on behalf of customers", "arranged for clients").
  - gross_aum, gross_sustainable_finance, portfolio_balance: cumulative/year-end stock or balance figures (e.g.
    "amounted to X at 31 December", "rose from X to Y", "total portfolio of X") rather than this year's new flow.
  - taxonomy_denominator, lending_portfolio_total, portfolio_share_or_growth, market_share: generic denominators,
    aggregate lending totals, or market-share/growth statistics, not SDG-linked finance.
  - credit_limit_undrawn: an "up to X", "limit of X", or "facility of up to X" ceiling with no financing/
    disbursement verb attached (e.g. a guarantee limit not yet drawn). If the text instead says something like
    "were financed", "disbursed", "provided", or "granted" for a concrete number of executed agreements, use
    disclosed_sdg_linked_finance even if "credit limit(s)" also appears as a parenthetical descriptor.
  - target / forward_commitment: forward-looking pledges, ambitions, or commitments not yet disbursed (e.g.
    "committed to issuing up to X within the next three years", "product range will cover X by 2025").
  - recipient_side_financing: loans, bonds, or facilities the REPORTING BANK ITSELF received/borrowed (e.g. "loan
    from the IBRD", "syndicated loan received by the Bank") -- liability-side funding into the bank, not the
    bank's own lending/financing out to customers or projects.
  - narrative_only or unknown: no concrete financial figure, or insufficient information to classify.

- sdg_support: explicit when the cited text names SDGs/tags for the amount, strong when the SDG link is strongly
  supported by the bank's description, weak for generic sustainability association, none when unsupported.
- relevant_sdgs: include only SDGs explicitly stated or strongly supported by the cited text; otherwise use an
  empty list.

Text:
{report_text}
""".replace("__BANK_REPORT_HYPHEN__", BANK_REPORT_LABEL.replace(" ", "-"))
