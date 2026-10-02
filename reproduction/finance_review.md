Finance adjudication review: 35 cached positive claims

Of the 35 finance rows currently marked `score_eligible=true` and `inclusion_policy=linked_scored`, **2 are retained and 33 excluded** under the requested current-year disbursement definition. The original cached total is **EUR 15,446,773,067.27**; the approved total for these reviewed claims is **EUR 7,031.77**. One retained row has an explicitly documented amount correction. These are finance adjudications, not recomputed honesty scores or verified impacts.

The machine-readable decisions are in [finance_adjudications.json](finance_adjudications.json). Each row preserves its checkpoint path, section, zero-based row index, exact original evidence and original EUR amount. **Downstream calculations must use `approved_amount_eur`**, including the adjustment for Sense 2023; summing the original amounts of included rows would incorrectly give EUR 7,884.61. No checkpoint, code, manuscript, or source file was edited.

The policy includes the bank’s own current-report-year disbursed SDG-linked finance and philanthropy. It excludes customer fund capital, AUM and holdings, year-end stocks, incoming bank-issued debt, historical issuance/refinancing, undrawn or unverified credit limits, duplicate claims, and amounts whose payer or disbursement year cannot be established. Reported execution must support the amount: a financing verb does not override an explicit credit-limit measure. No stock differences are interpreted as flows.

**Scope limitation:** this is a source-grounded review of the 35 cached positive claims only. It is not a complete external-data audit, an audit of all bank transactions, an assessment of actual impact, or a search for all missed finance disclosures. Rows already excluded/unlinked and false-negative extractions were not comprehensively reviewed. A zero below means no approved amount remains among this review’s cached positive claims for that country-year; it does not mean the banks had no SDG-related finance, or that the source corpus is complete. The prior CURRENT_STATUS figures are the input baseline, not the conclusion of this stricter review.

Included totals by country-year, calculated with decimal arithmetic:

| Country | Year | Reviewed | Included | Excluded | Original eligible EUR | Approved EUR |
|---|---:|---:|---:|---:|---:|---:|
| Finland | 2019 | 0 | 0 | 0 | 0.00 | 0.00 |
| Finland | 2020 | 4 | 0 | 4 | 1,320,005,000.00 | 0.00 |
| Finland | 2021 | 3 | 0 | 3 | 43,934,000.00 | 0.00 |
| Finland | 2022 | 5 | 0 | 5 | 2,581,486,500.00 | 0.00 |
| Finland | 2023 | 9 | 0 | 9 | 6,355,342,260.00 | 0.00 |
| Finland | 2024 | 5 | 1 | 4 | 4,723,667,980.00 | 6,250.00 |
| Ukraine | 2019 | 0 | 0 | 0 | 0.00 | 0.00 |
| Ukraine | 2020 | 2 | 0 | 2 | 174,800,000.00 | 0.00 |
| Ukraine | 2021 | 3 | 0 | 3 | 176,358,499.13 | 0.00 |
| Ukraine | 2022 | 1 | 0 | 1 | 44,770.38 | 0.00 |
| Ukraine | 2023 | 3 | 1 | 2 | 71,134,057.76 | 781.77 |
| Ukraine | 2024 | 0 | 0 | 0 | 0.00 | 0.00 |
| **Total** | **2019–2024** | **35** | **2** | **33** | **15,446,773,067.27** | **7,031.77** |

The two retained claims have source-established bank payments:

- **Oma Säästöpankki 2024: EUR 6,250, unchanged.** The company expressly reports the MIELI donation under 2024 grants and subsidies. The source is a two-page PDF spread: physical PDF page 110 contains printed pages 218–219; the donation is on printed page 218. The visible pagination governs, not the extraneous 114/115 footer text in the old parsed cache. The stored SDG 4/17 attribution is a column-joining error: that sentence describes financial-literacy work on printed page 219. The donation concerns youth mental health, with SDG 3 directly relevant; its SDG tags need separate correction before producing an SDG profile or score.
- **Sense Bank 2023: UAH 33,000 = EUR 781.77.** The school-supplies paragraph explicitly states UAH 69,000 of needs, UAH 36,000 raised by employees, and the bank financing the remainder. The original full-needs EUR 1,634.61 is therefore replaced by `(69000 - 36000) × 0.02369 = 781.77`. The existing checkpoint year-end 2023 FX factor and its conversion-source identifier are preserved; this review does not independently re-audit the FX table. `amount_adjustment.reason_code` is `remove_explicit_employee_funded_share`. This is an expressly reported contributor split, not an assumed grant or inferred annual loan flow.

The requested charity checks are documented individually below. Quoted wording comes from the original local PDF text, with whitespace collapsed; Ukrainian wording is preserved. PDF page numbers are physical, one-based pages, and report pagination is stated separately.

**Row 30: Sense Bank 2021, 96 тисяч гривень — exclude.** [Original report](<../data/bank_reports/reports/Ukrainian banks/2021/Sense_commission report_2021.pdf>), PDF 32 / report 30.

The report says 143 children received school items worth UAH 96,000 in 2021 under a project supported by the bank. It does not identify the bank as payer of that full amount or separate bank funding from any other contributors. Receipt of goods and a bank-supported programme establish activity, but not the bank's own disbursed share. Exclude as attribution ambiguity, without assuming staff financed it.

> Задля досягнення Цілі сталого розвитку №1 «Подолання бідності» Банк кілька років поспіль підтримує вихованців дитячих будинків та будинків-інтернатів в рамках проєктів: − «повний портфель « – задля забезпечення школярів усім необхідним до початку навчального року. − у 2021 році – 143 дитини з 6 закладів соціальної реабілітації отримали шкільний одяг, портфелі та канцелярію на загальну суму 96 тисяч гривень;

**Row 31: Sense Bank 2021, 1 712 878,40 гривень — exclude.** [Original report](<../data/bank_reports/reports/Ukrainian banks/2021/Sense_commission report_2021.pdf>), PDF 32 / report 30.

The report describes voluntary contributions to an employee's account, bank matching, and tax payments before reporting UAH 1 712 878,40 spent through Help Together in 2021. It does not state whether that programme total is the bank contribution, donor-plus-bank support, or inclusive of tax. The bank demonstrably participates, but its separately disbursed amount cannot be established. Do not include the full programme total or assume an arbitrary half as bank finance.

> Банк продовжує допомагати співробітникам та членам їх родин, які потрапили у біду: протягом визначеного періоду усі охочі можуть долучитися до допомоги колезі, перерахувавши кошти на рахунок співробітника. А Банк подвоює зібрану суму та сплачує податки у бюджет держави. У 2021 році за програмою «Допоможемо разом» витрачено 1 712 878,40 гривень. У проєкті взяли участь 40 співробітників Банку. У середньому збір для одного учасника склав 42 822 гривень.

**Row 32: Sense Bank 2022, 1 744 073,88 гривень — exclude.** [Original report](<../data/bank_reports/reports/Ukrainian banks/2022/Sense_annual report_2022.pdf>), PDF 35 / report 33.

The report describes voluntary contributions to an employee's account, bank matching, and tax payments before reporting UAH 1 744 073,88 spent through Help Together in 2022. It does not state whether that programme total is the bank contribution, donor-plus-bank support, or inclusive of tax. The bank demonstrably participates, but its separately disbursed amount cannot be established. Do not include the full programme total or assume an arbitrary half as bank finance.

> Банк продовжує допомагати співробітникам та членам їх родин, які потрапили у біду: протягом визначеного періоду усі охочі можуть долучитися до допомоги колезі, перерахувавши кошти на рахунок співробітника. А Банк подвоює зібрану суму та сплачує податки у бюджет держави. У 2022 році за програмою «Допоможемо разом» витрачено 1 744 073,88 гривень. У проекті взяли участь 25 співробітників Банку. У середньому збір для одного учасника склав 69 763 гривень.

**Row 33: Sense Bank 2023, 2 635 тисяч гривень — exclude.** [Original report](<../data/bank_reports/reports/Ukrainian banks/2023/Sense_annual report_2023.pdf>), PDF 61 / report lix.

The report describes voluntary contributions to an employee's account, bank matching, and tax payments before reporting UAH 2,635,000 spent through Help Together in 2023. It does not state whether that programme total is the bank contribution, donor-plus-bank support, or inclusive of tax. The bank demonstrably participates, but its separately disbursed amount cannot be established. Do not include the full programme total or assume an arbitrary half as bank finance.

> Банк продовжує допомагати співробітникам та членам їх родин, які потрапили у біду: протягом визначеного періоду усі охочі можуть долучитися до допомоги колезі, перерахувавши кошти на рахунок співробітника, а Банк подвоює зібрану суму та сплачує податки у бюджет Держави. У 2023 році за програмою «Допоможемо разом» витрачено 2 635 тисяч гривень. У проєкті взяли участь 36 співробітників Банку.

**Row 34: Sense Bank 2023, 69 тисяч гривень — include.** [Original report](<../data/bank_reports/reports/Ukrainian banks/2023/Sense_annual report_2023.pdf>), PDF 61 / report lix; PDF 62 / report lx.

The original passage states that school supplies were collected in 2023, total needs were UAH 69,000, employees raised UAH 36,000, and the bank financed the rest. The bank's explicitly attributable amount is therefore UAH 33,000, not the full UAH 69,000. Include only the documented remainder, converted with the checkpoint's existing 2023 rate: 33,000 × 0.02369 = EUR 781.77. This is a source-explicit funding split, not an assumed financing of all needs or a stock-to-flow inference.

> Пріоритетом у рамках цілі «Подолання бідності» Банк обрав категорію – допомога дітям з дитячих будинки.

> В рамках проєкту «Повний портфель» у 2023 році зібрали портфелі до школи дітям 2 закладів: Улянівська спеціальна школа для дітей-сиріт та дітей, позбавлених батьківського піклування (смт. Улянівка, Сумська область) та Дитячий будинок сімейного типу родини Міщенко (с. Горохуватка, Київська область). Загальна сума потреб – 69 тисяч гривень, з яких – 36 тисяч гривень зібрали співробітники Банку, а решту профінансував Банк.

**Row 26: Oma Säästöpankki 2024, EUR 6,250 — include.** [Original report](<../data/bank_reports/reports/Finnish banks/2024/omasp_annual_report_2024.pdf>), PDF 110 / report 218–219 (two-page spread; donation is on printed page 218).

The 'Highlights from 2024 grants and subsidies' list explicitly states that the Company donated EUR 6,250 to MIELI ry for youth mental health work. The amount, payer and report year are established; include unchanged as philanthropy. Visual inspection shows the cached SDG 4/17 phrase belongs to financial-literacy activities in the next column. The donation is health-related; its SDG tags need separate repair before any SDG-profile or score calculation.

> Through these actions, the Company supports the UN Sustainable Development Goals 3 Good health and wellbeing and 8 Decent work and economic growth. Highlights from 2024 grants and subsidies • The Company donated EUR 6,250 to MIELI ry for youth mental health work as part of the personnel's annual exercise challenge Kilsakisa.

The main non-charity corrections follow from the original wording and page context:

- Ålandsbanken 2020: EUR 2.8 million is explicitly cumulative since 1997 (PDF 3/report 2 and PDF 16/report 15). The EUR 500,000 yearly minimum is a general annual description, not a reconciled 2020 disbursement. The cross-referenced project page (PDF 10/report 9) confirms individual funding examples and a two-year award, but not the full cached EUR 500,000 as cash paid in 2020; that row is excluded as unverified, not classified as proof that no donation occurred. The EUR 40 million is new investor capital in a green bond fund.
- Aktia 2021/2022/2023: EUR 4 million describes existing infrastructure holdings; EUR 68 million is Bioindustry fund fundraising (not the Aktia Impact Fund/renewable-energy attribution in the saved justification); EUR 180 million is a fund subscription into the master fund. None establishes the bank’s own current-year disbursement. Savings Banks 2021 EUR 25.3 million is explicitly year-end investment-fund capital.
- Danske 2020: DKK 9.5 billion is a year-end mortgage-lending volume for a product launched in 2019. Danske 2023 and 2024: the four green-bond figures are expressly year-end nominal amounts of issued debt. They are bank funding liabilities and cannot be annual outgoing finance flows.
- Ålandsbanken 2021/2022: SEK 150 million is a December 2021 T2 issuance and then an outstanding T2 instrument. The 2023 Green Bonds table on PDF 174/report 173 actually labels its columns **2022 and 2021**, both 13.5; the cache’s 2023/2022 interpretation is wrong. Historical funding and allocation shares do not demonstrate a 2023 disbursement.
- OP 2022: keyword_categories[1] and investment_instruments[9] repeat the same April EUR 1 billion covered-bond issue; investment_instruments[8] is another bank-issued funding instrument. Source wording describes institutional investors and allocation of raised proceeds, not new project disbursements.
- OP 2023: keyword_categories[1], keyword_categories[3] and investment_instruments[10] are three extractions of one EUR 62 million year-end granted-loan total. All three are excluded because drawn amounts are unverified; the second and third carry duplicate references. The original `(0)` comparator and March product launch do not make a year-end total a gross cash-flow measure. The EUR 500 million and EUR 1 billion bonds are explicitly dated 2019 and 2022.
- OP 2024: EUR 500 million is labelled a green bond issued in 2024, while “Renewable energy” in the neighbouring dashboard concerns OP’s own power consumption. EUR 255 million (62) is explicitly the year-end total of granted SME green loans. Neither EUR 255 million nor a subtraction of the two balances is a verified 2024 disbursement.
- **Oschadbank source-year mismatch:** the manifest-labelled 2020 source PDF’s cover states “For the year ended 31 December 2019”; the management-report title on PDF 3 also says 2019. The EUR 144.8 million paragraph at PDF 12/report x describes 2019 corporate activity and concluded loan agreements. It cannot substantiate 2020 finance. This mismatch is reported for the root worker’s corpus/manuscript reconciliation; neither source files nor year assignments were changed here.
- Ukrgazbank 2020: EUR 30 million is a loan to the bank from IFC, agreed at the beginning of 2021 and potentially convertible to the bank’s equity. It is both recipient-side and outside 2020. Ukrgazbank 2023: the original “were financed” sentence expressly denominates the over-UAH-3-billion amount as “credit limits”; context on PDF 132–133/report 130–131 does not establish the amount actually drawn.
- Raiffeisen 2021: the 30% environmental condition is attached to the preceding EBRD Guarantee for Growth mechanism of up to EUR 75 million. The EUR 176.3 million paragraph concerns a different EIB/EIF EU4Business SME programme, increased “last year” and utilised by year-end. Combining the two paragraphs does not substantiate the cached SDG-linked 2021 amount, and applying 30% to EUR 176.3 million would also be unsupported.

The complete row ledger follows. Row numbers are one-based positions in the adjudication JSON array, while `K[i]` means the zero-based `keyword_categories[i]` and `I[i]` means `investment_instruments[i]`. The JSON contains the exact checkpoint path, complete rationale, source quotations, and any duplicate identity for each row.

| Row | Country/year · bank | Identity | Original EUR | Decision | Approved EUR | Reason | Source PDF page(s) |
|---:|---|---|---:|---|---:|---|---|
| 1 | Finland 2020 · Ålandsbanken | K[0] | 500,000.00 | exclude | 0.00 | current_year_disbursement_not_verified | [10, 16](<../data/bank_reports/reports/Finnish banks/2020/Ålandsbanken Abp annual and sustainability report 2020.pdf>) |
| 2 | Finland 2020 · Ålandsbanken | K[1] | 2,800,000.00 | exclude | 0.00 | cumulative_historical_total | [3, 16](<../data/bank_reports/reports/Finnish banks/2020/Ålandsbanken Abp annual and sustainability report 2020.pdf>) |
| 3 | Finland 2020 · Ålandsbanken | I[0] | 40,000,000.00 | exclude | 0.00 | customer_fund_subscriptions | [20](<../data/bank_reports/reports/Finnish banks/2020/Ålandsbanken Abp annual and sustainability report 2020.pdf>) |
| 4 | Finland 2020 · Danske Bank | I[1] | 1,276,705,000.00 | exclude | 0.00 | year_end_portfolio_stock | [44](<../data/bank_reports/reports/Finnish banks/2020/Danske Bank_Annual Report 2020.pdf>) |
| 5 | Finland 2021 · Aktia Pankki | K[0] | 4,000,000.00 | exclude | 0.00 | investment_holding_stock | [55](<../data/bank_reports/reports/Finnish banks/2021/Aktia_Annual_review_2021.pdf>) |
| 6 | Finland 2021 · Ålandsbanken | K[1] | 14,634,000.00 | exclude | 0.00 | bank_issued_funding_liability | [40](<../data/bank_reports/reports/Finnish banks/2021/Ålandsbanken Abp annual and sustainability report 2021.pdf>) |
| 7 | Finland 2021 · Säästöpankkien Keskuspankki | K[0] | 25,300,000.00 | exclude | 0.00 | customer_fund_aum_stock | [40](<../data/bank_reports/reports/Finnish banks/2021/Säästöpankkien Savings bank SustainabilityReport_2021.pdf>) |
| 8 | Finland 2022 · Aktia Pankki | K[0] | 68,000,000.00 | exclude | 0.00 | customer_fund_subscriptions | [51](<../data/bank_reports/reports/Finnish banks/2022/Aktia_Annual_review_2022.pdf>) |
| 9 | Finland 2022 · Ålandsbanken | I[0] | 13,486,500.00 | exclude | 0.00 | outstanding_bank_funding_liability | [33](<../data/bank_reports/reports/Finnish banks/2022/Ålandsbanken Abp annual and sustainability report 2022.pdf>) |
| 10 | Finland 2022 · OP Yrityspankki | K[1] | 1,000,000,000.00 | exclude | 0.00 | bank_issued_funding_liability | [19](<../data/bank_reports/reports/Finnish banks/2022/op_Financial Groups Report by the Board of Directors and Financial Statements 2022.pdf>) |
| 11 | Finland 2022 · OP Yrityspankki | I[8] | 500,000,000.00 | exclude | 0.00 | bank_issued_funding_liability | [19](<../data/bank_reports/reports/Finnish banks/2022/op_Financial Groups Report by the Board of Directors and Financial Statements 2022.pdf>) |
| 12 | Finland 2022 · OP Yrityspankki | I[9] | 1,000,000,000.00 | exclude | 0.00 | duplicate_claim | [19](<../data/bank_reports/reports/Finnish banks/2022/op_Financial Groups Report by the Board of Directors and Financial Statements 2022.pdf>) |
| 13 | Finland 2023 · Aktia Pankki | K[2] | 180,000,000.00 | exclude | 0.00 | customer_fund_subscriptions | [54](<../data/bank_reports/reports/Finnish banks/2023/Aktia_Annual Review_2023.pdf>) |
| 14 | Finland 2023 · Ålandsbanken | I[2] | 13,500,000.00 | exclude | 0.00 | historical_bank_funding_stock | [174](<../data/bank_reports/reports/Finnish banks/2023/Ålandsbanken Abp annual and sustainability report 2023.pdf>) |
| 15 | Finland 2023 · Danske Bank | I[6] | 3,250,242,140.00 | exclude | 0.00 | year_end_bank_funding_liability | [142](<../data/bank_reports/reports/Finnish banks/2023/Danske Bank_Annual Report 2023.pdf>) |
| 16 | Finland 2023 · Danske Bank | I[7] | 1,225,600,120.00 | exclude | 0.00 | year_end_bank_funding_liability | [142](<../data/bank_reports/reports/Finnish banks/2023/Danske Bank_Annual Report 2023.pdf>) |
| 17 | Finland 2023 · OP Yrityspankki | K[1] | 62,000,000.00 | exclude | 0.00 | year_end_granted_loans_not_verified_disbursed | [30](<../data/bank_reports/reports/Finnish banks/2023/op-financial-groups-year-and-sustainability2023.pdf>) |
| 18 | Finland 2023 · OP Yrityspankki | K[3] | 62,000,000.00 | exclude | 0.00 | duplicate_claim | [40](<../data/bank_reports/reports/Finnish banks/2023/op_Financial Groups Report by the Board of Directors and Financial Statements 2023.pdf>) |
| 19 | Finland 2023 · OP Yrityspankki | I[5] | 500,000,000.00 | exclude | 0.00 | historic_bank_issuance | [17](<../data/bank_reports/reports/Finnish banks/2023/op_Financial Groups Report by the Board of Directors and Financial Statements 2023.pdf>) |
| 20 | Finland 2023 · OP Yrityspankki | I[8] | 1,000,000,000.00 | exclude | 0.00 | historic_bank_issuance | [17](<../data/bank_reports/reports/Finnish banks/2023/op_Financial Groups Report by the Board of Directors and Financial Statements 2023.pdf>) |
| 21 | Finland 2023 · OP Yrityspankki | I[10] | 62,000,000.00 | exclude | 0.00 | duplicate_claim | [40](<../data/bank_reports/reports/Finnish banks/2023/op_Financial Groups Report by the Board of Directors and Financial Statements 2023.pdf>) |
| 22 | Finland 2024 · Danske Bank | I[0] | 2,750,856,350.00 | exclude | 0.00 | year_end_bank_funding_liability | [181](<../data/bank_reports/reports/Finnish banks/2024/Danske Bank_Annual Report 2024.pdf>) |
| 23 | Finland 2024 · Danske Bank | I[1] | 1,217,805,380.00 | exclude | 0.00 | year_end_bank_funding_liability | [181](<../data/bank_reports/reports/Finnish banks/2024/Danske Bank_Annual Report 2024.pdf>) |
| 24 | Finland 2024 · OP Yrityspankki | K[0] | 500,000,000.00 | exclude | 0.00 | bank_issued_funding_liability | [9](<../data/bank_reports/reports/Finnish banks/2024/op-financial-groups-annual-report-2024.pdf>) |
| 25 | Finland 2024 · OP Yrityspankki | K[2] | 255,000,000.00 | exclude | 0.00 | year_end_granted_loans_not_verified_disbursed | [53](<../data/bank_reports/reports/Finnish banks/2024/op-financial-groups-annual-report-2024.pdf>) |
| 26 | Finland 2024 · Oma Säästöpankki | K[0] | 6,250.00 | include | 6,250.00 | bank_donation_current_year_verified | [110](<../data/bank_reports/reports/Finnish banks/2024/omasp_annual_report_2024.pdf>) |
| 27 | Ukraine 2020 · Oschadbank | K[0] | 144,800,000.00 | exclude | 0.00 | source_report_year_mismatch | [1, 3, 12](<../data/bank_reports/reports/Ukrainian banks/2020/Oshchadbank_annual report_2020.pdf>) |
| 28 | Ukraine 2020 · Ukrgazbank | K[0] | 30,000,000.00 | exclude | 0.00 | recipient_side_future_financing | [30](<../data/bank_reports/reports/Ukrainian banks/2020/ugb_management report_2020.pdf>) |
| 29 | Ukraine 2021 · Raiffeisen Bank JSC | K[0] | 176,300,000.00 | exclude | 0.00 | cross_program_sdg_link_and_year_not_verified | [52](<../data/bank_reports/reports/Ukrainian banks/2021/Raiffeisen_annual report_2021.pdf>) |
| 30 | Ukraine 2021 · Sense Bank | K[0] | 3,104.64 | exclude | 0.00 | bank_funded_share_not_verified | [32](<../data/bank_reports/reports/Ukrainian banks/2021/Sense_commission report_2021.pdf>) |
| 31 | Ukraine 2021 · Sense Bank | K[1] | 55,394.49 | exclude | 0.00 | mixed_funding_program_total_not_attributable | [32](<../data/bank_reports/reports/Ukrainian banks/2021/Sense_commission report_2021.pdf>) |
| 32 | Ukraine 2022 · Sense Bank | K[0] | 44,770.38 | exclude | 0.00 | mixed_funding_program_total_not_attributable | [35](<../data/bank_reports/reports/Ukrainian banks/2022/Sense_annual report_2022.pdf>) |
| 33 | Ukraine 2023 · Sense Bank | K[0] | 62,423.15 | exclude | 0.00 | mixed_funding_program_total_not_attributable | [61](<../data/bank_reports/reports/Ukrainian banks/2023/Sense_annual report_2023.pdf>) |
| 34 | Ukraine 2023 · Sense Bank | K[2] | 1,634.61 | include | 781.77 | bank_funded_share_verified | [61, 62](<../data/bank_reports/reports/Ukrainian banks/2023/Sense_annual report_2023.pdf>) |
| 35 | Ukraine 2023 · Ukrgazbank | K[0] | 71,070,000.00 | exclude | 0.00 | credit_limits_not_verified_drawn | [132, 133](<../data/bank_reports/reports/Ukrainian banks/2023/ugb_annualreport_2023.pdf>) |

Validation covered exactly 35 eligible source identities and 35 unique adjudication identities, with no missing or extra rows and no original-evidence or original-amount guard mismatches. All 23 cited original PDFs were locally materialized and read at the relevant pages. The manifest-to-source paths and checkpoint/PDF SHA-256 hashes were verified before writing. Source excerpts were checked against whitespace-normalized extraction from the original PDFs. Four layout-sensitive pages were also rendered in memory and visually inspected: Aktia 2022 PDF 51, Ålandsbanken 2023 PDF 174, Oma 2024 PDF 110, and Sense 2023 PDF 62. No rendered artifacts were saved.

The financial decisions do not endorse the original SDG tags. In particular, the retained Oma donation’s [4, 17] tags need repair; Sense’s school-supplies project appears in a poverty-reduction context and has an education purpose, so its explicit-versus-thematic tagging also needs a separate check. No score or SDG-level share should be described as fully corrected based solely on these finance files.

Reproduce the identity checks and approved totals locally from the repository root, without model calls:

```python
import json
from collections import defaultdict
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

p = json.loads(Path("reproduction/finance_adjudications.json").read_text())
base = Path("evaluations/reruns/country_year_classification_20260630_211343")
eligible = {}
for checkpoint in sorted(base.glob("*/checkpoints_corrected/*.json")):
    obj = json.loads(checkpoint.read_text())
    for section in ("keyword_categories", "investment_instruments"):
        for index, row in enumerate(obj.get("investments", {}).get(section, [])):
            if row.get("score_eligible") is True and row.get("inclusion_policy") == "linked_scored":
                eligible[(str(checkpoint), section, index)] = row
actual = {(r["checkpoint"], r["section"], r["row_index"]): r for r in p["rows"]}
assert len(p["rows"]) == len(actual) == len(eligible) == 35
assert actual.keys() == eligible.keys()
assert sum(r["decision"] == "include" for r in p["rows"]) == 2
assert sum(r["decision"] == "exclude" for r in p["rows"]) == 33
totals = {(c, y): Decimal(0) for c in ("Finland", "Ukraine") for y in range(2019, 2025)}
hashes = {}
for identity, row in actual.items():
    assert row["original_evidence"] == eligible[identity]["evidence"]
    assert row["original_amount_eur"] == eligible[identity]["amount_eur"]
    for kind in ("checkpoint", "source_report"):
        path = row[kind]
        if path not in hashes:
            hashes[path] = sha256(Path(path).read_bytes()).hexdigest()
        assert hashes[path] == row[kind + "_sha256"]
    approved = Decimal(str(row["approved_amount_eur"]))
    assert (approved > 0) == (row["decision"] == "include")
    if row["decision"] == "include" and approved != Decimal(str(row["original_amount_eur"])):
        assert "amount_adjustment" in row
    totals[(row["country"], row["year"])] += approved
for identity, total in sorted(totals.items()):
    print(*identity, f"{total:.2f}")
assert sum(totals.values()) == Decimal("7031.77")
```

Neither output file existed at the initial inventory or final write check; this creates the completed adjudications and review, not a placeholder.
