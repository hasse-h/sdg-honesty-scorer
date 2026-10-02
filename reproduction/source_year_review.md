Source year and identity audit — 12 September 2026

Audited **181/181 entries across 152 bank-years**, Finland/Ukraine 2019–2024. All are materialized PDFs. The 12 country-year manifests exactly reproduce bank_reports_all.csv; entries are counted once, with both manifest locations recorded in [source_year_audit.json](source_year_audit.json).

**Reporting year: 178 verified, 3 mismatches, 0 uncertain/unknown.** JSON field `decision` concerns source year; `entity_attribution.decision` records identity findings separately.

| Quarantine checkpoint | Actual period | Original-source evidence |
| --- | --- | --- |
| Ukraine / Oschadbank / 2020 — entry 109 | 2019 | PDF p. 1: “For the year ended 31 December 2019”; management title p. 3 confirms 2019. |
| Ukraine / Raiffeisen Bank JSC / 2023 — entry 160 | 2022 | PDF p. 1: “For the year ended 31 December 2022”; chairman’s foreword p. 4 explicitly describes 2022. |
| Ukraine / Universal Bank / 2023 — entry 166 | 2022 | PDF p. 1: “Річна інформація емітента цінних паперів”, reporting-year field “за рік 2022”. The 13.11.2023 registration/publication date does not establish the reporting year. |

**Exclude all three bank-years; do not relabel cached narrative or financial extraction.** Each has one manifest report and no independent correct-year report within that bank-year. No separable cached extraction was proved. The same quarantine rule applies to multi-file bank-years containing any wrong-year source; none of the 29 multi-file bank-years has a confirmed wrong-year source here.

Oschadbank SHA-256: `059a39e36d1bba5572ef781bfbb15c3a31961e681c48285ebfd8ea5f60d80728`, corroborating the supplied finance_adjudications.json finding directly on the original PDF. All full hashes and repo-relative report paths are in the JSON.

**Exact duplicates: 177 distinct PDF hashes; four duplicate groups.**

| Entries | Duplicate assignments | Source identification |
| --- | --- | --- |
| 1, 2 | Aktia 2019 annual/financial filenames | Same bank/year; identical PDF bytes. |
| 29, 33 | Alisa 2021 / Fellow 2021 annual reports | “FELLOW FINANCE PLC ANNUAL REPORT 2021”. |
| 30, 32 | Evli 2021 / Fellow 2021 financial statements | “FELLOW FINANCE PLC FINANCIAL STATEMENTS BULLETIN JANUARY-DECEMBER 2021”. |
| 144, 160 | Raiffeisen 2022 / 2023 | Both report 2022. |

Oschadbank entries 93/109 and Universal Bank entries 150/166 have **different PDF hashes but identical extracted text on pages 1–8**. They are not byte-identical PDFs; full-document text equality was not tested.

Identity results are separate: **144 verified source-name attributions, 36 uncertain, 1 confirmed conflict**.

- **Evli 2021, entry 30:** the original identifies Fellow Finance. Entry 31 independently identifies Evli Bank Plc, but separation of the existing extraction is unproven; entity attribution still requires a decision.
- **Alisa/Evli/Fellow:** eight uncertain entries comprise Fellow Finance assigned to Fellow Pankki (5, 6, 13, 14, 32, 33), Fellow Finance assigned to Alisa (29), and Fellow Bank assigned to Alisa (46). Entry 46 p. 3 describes the 2 April 2022 formation/merger. No legal continuity or retrospective reassignment is inferred; all 19 alias-family entries are flagged.
- **Different issuer/group scope:** 26 entries assigned to Bonum, OP Yrityspankki, Säästöpankkien Keskuspankki or Suomen Asuntohypopankki instead identify POP Bank Group, OP Financial Group, Savings Banks Group or The Mortgage Society of Finland/Suomen Hypoteekkiyhdistys. Their years are verified; attribution to the specific checkpoint bank remains uncertain.
- **Historical names:** Raiffeisen 2019/2020 identify Raiffeisen Bank Aval; the bounded pages did not independently settle the later-name mapping. Sense 2019–2021 identify ALFA-BANK; entry 145 p. 3 explicitly documents the 2022 change to АТ «СЕНС БАНК», and the historical names are retained.
- **Country scope:** the six Danske reports identify Danske Bank Group. The Finland checkpoint label does not establish Finland-only coverage.

Method and limits: deterministic local fitz first-page extraction, then targeted pages within the first eight; no later pages were needed. Covers for entries 3 (Evli 2019), 106 (Kredobank 2020) and 164 (Ukrsibbank 2023) required in-memory fitz rendering and marked visual transcription because cover text omitted the year or was empty. Quotes retain their original languages with whitespace normalization. Titles and explicit management-period statements establish years; expected-year appearances in accounting comparatives do not.

This audit covers year/entity attribution only, without assessing SDGs, amounts, accounting classification, FX or scores. No extraction caches/checkpoints were used as period evidence or changed. Only these two audit files were written; no model/API classification calls, pipeline re-extraction, nested agents, code/manuscript edits, commits or pushes were performed.

Validation: 181/181 coverage reconciled; all source hashes rechecked; every text-extracted quote verified against its cited PDF page. The three visual transcriptions are explicitly distinguished.
