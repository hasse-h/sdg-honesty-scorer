# Section 4.5 full-window composition analysis (2026-07-08)

Extends the paper's Section 4.5 SDG composition-of-divergence analysis from
the 2024 endpoint to the full 2019-2024 window, computed from the corrected
checkpoints under
`evaluations/reruns/country_year_classification_20260630_211343/<stem>/checkpoints_corrected/`.

## Files

- `compute_sdg_profiles_full_window.py` — computes country-year narrative
  profiles (share of retained priority-weighted mentions, centrality >= 3)
  and finance profiles (share of score-eligible SDG-tagged amounts;
  multi-SDG rows count toward every tag).
- `sdg_profiles_by_country_year.csv` — per country-year-SDG shares and gaps.
- `sdg_profiles_pooled_2019_2024.csv` — pooled over the window.
- `reproduction_check_2024.txt` — the pipeline reproduces all 14 values in
  the paper's previous (2024-only) Figure 5 exactly (max |diff| 0.0 pp),
  so the full-window numbers extend the published methodology 1:1.
- `make_figure5_full_window.py` / `figure_5_sdg_gap_heatmap_2019_2024.png` —
  the replacement Figure 5: SDG x year gap heatmaps per country. Diverging
  blue/red matches the poles used in the paper's existing figures; the
  scale is capped at +/-50 pp with the one out-of-range cell (Ukraine 2022
  SDG 3, -94.0, a single EUR 44,770 row) annotated with its actual value.

## Headline full-window facts (cited in the revised Section 4.5)

- Finance profiles are compositionally static: SDG 7 + SDG 13 carry
  >= 99.87% of tagged score-eligible amounts in every non-zero country-year
  except degenerate Ukraine 2022 (single EUR 44,770 row tagged SDG 3).
  Only other tags ever present: Finland 2020 SDG 14 (EUR 3.3m) and scattered
  rows < EUR 0.1m.
- Finland's largest uncovered claims are SDGs 8, 16, 12 in every year
  (each +8.6 to +13.9 pp); in zero-finance 2019, SDG 13 itself (+23.3 pp)
  leads.
- Ukraine's largest uncovered claims are SDGs 16 (+20.6 to +35.9 pp),
  8 (+18.4 to +24.8 pp) and 9 in all six years.
- Zero score-eligible finance country-years: Finland 2019, Ukraine 2019,
  Ukraine 2024 (verified zeros, per CURRENT_STATUS.md).

## Paper application

Applied to the manuscript by
`/Users/hasse_h/tmp/apply_section45_full_window.py`, producing
`SDGwashing_paper_alternative_20260708_fusion_revised_honesty_epigraph_no_ref_fusion_edits_sec45_full_window.docx`
(retitled Section 4.5, replaced both body paragraphs and Figure 5, updated
the Section 4.1 overview item). Appendix C remains the 2024 endpoint
decomposition; the per-year decomposition lives in the CSVs here.
