# Phase 7 FCF Output Interpretation Guide

## Why This File Exists

This guide explains, in plain English, how to read the Phase 7 CSV files in `outputs/phase7/`. Phase 7 repeats the EPS factor work but for Free Cash Flow per share, and adds a combined EPS-vs-FCF panel.

If you are staring at the CSVs wondering:

- what am I supposed to learn from these numbers?
- which file answers which question?
- what does a "log contribution" or a "weight" actually mean?

this file is meant to answer that.

## Two Concepts That Apply Everywhere

### 1. `window_label` (the look-back window)

Every per-year-pair file carries a `window_label` of `2015_2025`, `2010_2025`, or `2001_2025`. These are the three replication windows (Years 1-10, 1-15, 1-20). The same year-pair (for example `2019-2020`) appears in more than one window on purpose - it is not duplicated data, it just belongs to each window that contains it. If you only want the long history, filter to `window_label == 2001_2025`.

### 2. Log contribution (the unit used for every "contribution" column)

All columns ending in `_log_contribution` (and `_log_change`) are measured in log points. The key properties:

- They are **additive**: the factor contributions for a period add up exactly to the total change for that period.
- A value near `0.10` means roughly a `+10%` effect; `-0.10` means roughly `-10%`.
- Positive = the factor helped FCF/S (or EPS) go up. Negative = it dragged it down.
- Share count is signed so that **buybacks (falling share count) read as a positive contribution**.

Why logs instead of plain percentages? Because plain percentage changes do not add up cleanly when several drivers move at once. Logs do, which is why every "tie-out" check in the validation file is exactly zero.

## The Two FCF Identities

```text
FCF/S = Rev/S x FCF Margin                 (two-factor view)
FCF/S = Revenue x FCF Margin / Shares      (three-factor view)
```

where:

- `Rev/S` = Revenue per Share = `Revenue / Shares`
- `FCF Margin` = `Free Cash Flow / Revenue`
- `FCF/S` = Free Cash Flow per Share = `Free Cash Flow / Shares`

These mirror the EPS identities (`EPS = Rev/S x Net Margin` and `EPS = Revenue x Net Margin / Shares`). The only factor that differs between the EPS and FCF bridges is the margin: net margin for EPS, FCF margin for FCF.

## File-by-File Guide

### 1. `phase7_fcf_annual_tables.csv` - the raw building blocks

One row per year. Everything else in Phase 7 is derived from this file.

| Column | Meaning |
| --- | --- |
| `window_label`, `year` | Which window and which calendar year |
| `revenue`, `net_income`, `free_cash_flow` | Base figures from `Model.csv`, in $m |
| `average_diluted_shares` | Diluted share count, in millions |
| `net_margin` | `net_income / revenue` |
| `fcf_margin` | `free_cash_flow / revenue` |
| `rev_per_share` | `revenue / shares` |
| `eps` | `net_income / shares` |
| `fcf_per_share` | `free_cash_flow / shares` |

Sanity check you can do by hand: `fcf_per_share = rev_per_share x fcf_margin` exactly.

### 2. `phase7_fcf_two_factor_yoy.csv` - FCF/S = Rev/S x FCF Margin

One row per year-pair (the `period` column, e.g. `2019-2020`). This is the simplest view: it splits each year's FCF/S move into just two pieces.

| Column | Meaning |
| --- | --- |
| `delta_rev_per_share_growth`, `delta_fcf_margin_growth`, `delta_fcf_per_share_growth` | Simple year-over-year % change (e.g. `0.34` = +34%) |
| `rev_per_share_log_contribution` | How much Rev/S moved FCF/S (log points) |
| `fcf_margin_log_contribution` | How much FCF margin moved FCF/S (log points) |
| `fcf_per_share_log_change` | Total FCF/S move = the two contributions added |
| `two_factor_tie_out_gap` | Always ~0; proves the bridge is exact |
| `dominant_two_factor` | Which of the two mattered more that year |

**Reading a row:** in `2019-2020`, Rev/S contributed `+0.1368` and FCF margin `+0.2043`, so FCF/S rose `+0.3411`, and `fcf_margin` was the bigger driver.

### 3. `phase7_fcf_three_factor_decomposition.csv` - FCF/S = Revenue x FCF Margin / Shares

The richest file. Same year-pairs, but the FCF/S move is split into three factors, then ranked and weighted.

| Column | Meaning |
| --- | --- |
| `revenue_growth`, `fcf_margin_growth`, `share_count_growth`, `fcf_per_share_growth` | Simple year-over-year % changes |
| `share_count_effect_simple` | `-share_count_growth` (buybacks shown as positive) |
| `revenue_log_contribution` | Revenue's contribution to FCF/S |
| `fcf_margin_log_contribution` | FCF margin's contribution |
| `share_count_log_contribution` | Share count's contribution (signed: buybacks positive) |
| `rev_per_share_log_contribution` | Revenue + share-count contributions combined (the Rev/S piece) |
| `fcf_per_share_log_change` | Total FCF/S move = the three factor contributions added |
| `tie_out_gap` | Always ~0; proves the three-factor bridge is exact |
| `rank_1_factor` / `rank_2_factor` / `rank_3_factor` | The three factors ordered by magnitude, biggest first |
| `rank_1_log_contribution` (etc.) | The contribution value for each ranked factor |
| `revenue_weight_abs_share`, `fcf_margin_weight_abs_share`, `share_count_weight_abs_share` | Each factor as a share of total absolute movement; the three sum to 1.0 |
| `largest_driver` + `largest_driver_direction` | The single biggest factor and whether it was `positive` or `negative` |
| `largest_driver_abs_log_contribution` | Size of that biggest factor |
| `has_offsetting_factors` | `yes` when at least one factor pushed up while another pushed down |
| `fcf_per_share_direction` | Did FCF/S rise or fall overall that year |

**Weights explained:** the `_weight_abs_share` columns answer "what share of this year's total factor activity came from each driver." If `revenue_weight_abs_share = 0.55`, revenue accounted for 55% of the absolute movement. They are always positive and always sum to 100%, which is the weighting scheme chosen for Phase 7.

**This file answers:** "which factor drove FCF that year" (`largest_driver` / `rank_1_factor`), "how much did each contribute" (the contribution columns), and "did drivers fight each other" (`has_offsetting_factors`).

### 4. `phase7_combined_six_factor_panel.csv` - EPS vs FCF side by side

One row per year-pair (in the `2001_2025` window). It pairs the EPS bridge and the FCF bridge so you can compare them directly.

| Column | Meaning |
| --- | --- |
| `eps_revenue_log_contribution`, `eps_net_margin_log_contribution`, `eps_share_count_log_contribution` | The three EPS factors |
| `eps_log_change` | Total EPS move that year |
| `fcf_revenue_log_contribution`, `fcf_margin_log_contribution`, `fcf_share_count_log_contribution` | The three FCF factors |
| `fcf_per_share_log_change` | Total FCF/S move that year |
| `eps_*_weight`, `fcf_*_weight` | Absolute-share weights within each metric (each trio sums to 1) |
| `net_margin_minus_fcf_margin_contribution` | How much more net margin helped EPS than FCF margin helped FCF that year |
| `share_count_sensitivity_gap` | `fcf_share_count - eps_share_count` |

Two things to notice:

- `eps_revenue` equals `fcf_revenue`, and `eps_share_count` equals `fcf_share_count`, on every row. That is expected: revenue and share count are shared by both metrics. Only the margin term differs.
- Because of that, `share_count_sensitivity_gap` is `0` on every row, which confirms buybacks lift EPS and FCF/S by the exact same amount. The cleanest "where the two metrics diverge" column is `net_margin_minus_fcf_margin_contribution`.

### 5. `phase7_fcf_factors_sheet_style.csv` - the Sheet1-style block

This reproduces the original formulas-sheet layout for the Years 1-5 replication (2015-2020), so it is easy to eyeball against `data/GOOG EPS Formulas ML Project/Sheet1.csv`.

- Top block: `delta Rev/Share`, `delta FCFMargin`, `delta FCF (additive)` - the simple year-over-year growth rates, where `delta FCF = delta Rev/Share + delta FCFMargin` (the additive convention the sheet uses).
- Middle block: the same `delta Rev/Share` plus the EPS-side `delta NetMargin` and `delta EPS (additive)`, so the six factors sit together.
- Bottom block: the underlying levels (`Rev`, `FCF`, `Net Income`, `#Shares`, `Rev/S`, `FCFMargin`, `FCF/S`, `NetMargin`).

Note: this block uses the simple additive convention to match the sheet; the exact (log) decomposition lives in files 2-4. `Year 1` reproduces the sheet's `delta Rev/Share` exactly as a tie-out check.

### 6. `phase7_fcf_validation_results.csv` - the proof it is correct

One row per test, each marked `PASS` or `FAIL`. It checks row counts per window, the exact accounting identity, the two- and three-factor log tie-outs (gap = 0), that all inputs are positive, that buybacks map to positive share-count contributions, that the weights sum to 1, and that the combined panel joined completely. All rows currently read `PASS`.

### 7. `phase7_fcf_summary.md` - the narrative answers

A standalone write-up of the answered questions for FCF and the six-factor view. The same content also lives in the consolidated `reports/EPS-analysis-question-answers.md` under the Phase 7 section.

## Quick "Where Do I Look?" Index

| I want to know... | Look here |
| --- | --- |
| The raw revenue / FCF / shares for a year | `phase7_fcf_annual_tables.csv` |
| Simple Rev/S vs FCF-margin split for a year | `phase7_fcf_two_factor_yoy.csv` |
| Which factor drove FCF, ranked and weighted | `phase7_fcf_three_factor_decomposition.csv` |
| How EPS and FCF compare in the same year | `phase7_combined_six_factor_panel.csv` |
| A sheet-style view of Years 1-5 | `phase7_fcf_factors_sheet_style.csv` |
| Whether the numbers are validated | `phase7_fcf_validation_results.csv` |
| Plain-English answers to the questions | `phase7_fcf_summary.md` or the Phase 7 section of `EPS-analysis-question-answers.md` |

## Important Caveat (carried from earlier phases)

The 2013-2014 period contains a share-basis break (the diluted share count jumps), which makes the `2013-2014` row an outlier in any window that includes it (`2010_2025` and `2001_2025`). Treat that single year's share-count swing as a data artifact rather than a clean operating signal. It affects FCF/S exactly as it affects EPS.
