# EPS Analysis Executive Summary

## Objective

Analyze how changes in:

- `Revenue per Share (Rev/S)`
- `Net Margin`
- `Share Count`

affect `EPS`, using the Google data in `data/GOOG MS ML 10-Year Actuals/Model.csv` and the methodology shown in `data/GOOG EPS Formulas ML Project/Sheet1.csv`.

This work was completed in four phases:

1. Replicate the formulas-sheet logic for the `2015-2020` sample.
2. Expand that methodology to `2015-2025`, `2010-2025`, and `2001-2025`.
3. Build an exact three-factor EPS decomposition.
4. Answer the business questions using the generated outputs.

---

## Executive Takeaways

- The formulas sheet was successfully replicated.
- The formulas sheet uses `2015` as a base year and annualizes each horizon.
- The formulas sheet `∆EPS` row is an additive approximation, not the true EPS CAGR.
- The methodology was successfully expanded to `2015-2025`, `2010-2025`, and `2001-2025`.
- An exact three-factor decomposition was built using `Revenue`, `Net Margin`, and `Share Count`.
- Over the `2020-2025` year-over-year periods, `Revenue` was the most consistent positive contributor to EPS growth.
- Over the same `2020-2025` period, `Net Margin` was the most volatile factor.
- The biggest full-history factor swing appears in `2013-2014` and is driven by `Share Count`, but that result should be treated cautiously because of the apparent share-basis break around 2014.
- Excluding that break year, the largest single factor swing in the long history is a positive `Revenue` contribution in `2001-2002`.

---

## What Was Built

### Phase 1

Rebuilt the `2015-2020` annual table and verified the formulas sheet logic.

Key result:

- `∆Rev/Share`, `∆NetMargin`, and sheet-style `∆EPS` matched the formulas sheet exactly.

Important interpretation:

- `∆EPS` in the formulas sheet is not the true EPS CAGR.
- It is the additive approximation:

```text
∆EPS ≈ ∆Rev/Share + ∆NetMargin
```

### Phase 2

Expanded the same formulas-sheet methodology to:

- `2015-2025`
- `2010-2025`
- `2001-2025`

Key result:

- The expansion worked mechanically and all requested windows were generated.

Important interpretation:

- The gap between the additive approximation and the true EPS CAGR becomes much larger in older windows.
- That is especially noticeable in the long-history view.

### Phase 3

Built the exact three-factor decomposition using:

```text
EPS = Revenue x Net Margin / Shares
```

This phase split EPS movement into:

- `Revenue`
- `Net Margin`
- `Share Count`

Key result:

- The decomposition ties out exactly back to EPS movement.

### Phase 4

Converted the decomposition outputs into business answers, rankings, rolling analysis, and relationship checks.

Key result:

- The requested questions can now be answered directly from the exported files.

---

## Main Findings

## 1. Replication And Expansion

- The original formulas-sheet sample for `2015-2020` was replicated successfully.
- The same methodology was extended to `2015-2025`, `2010-2025`, and `2001-2025`.
- There is now both a two-factor view and a three-factor view of EPS change.

## 2. Year-Over-Year Decomposition

- The largest factor swing in the full `2001-2025` output is `Share Count` in `2013-2014`, and it is negative.
- That result is almost certainly distorted by the share-basis change around 2014.
- Excluding that break year, the largest factor swing is `Revenue` in `2001-2002`, and it is positive.

The largest factor swing in the full 2001 to 2025 output is Share Count in 2013-2014, and it isa negative value
That result is almost certainly distorted by the share-basis change around 2014. The share basis change was basically when the shares got split. When shares get split, the you technically own the same amount of share value. Say you haev 5 shares at $4 each, that would mean you own 20 shares worth. Lets say a split happens and now you own 10 shares at $4 each. You still own $20 worth of shares, they are just distributed differently. Excluding that break year, the largest factor swing is Revenue in 2001-2002 and it is positive. 



## 3. Five-Year Rolling Analysis

Using the `2020-2025` year-over-year periods:

- The most consistent positive contributor is `Revenue`.
- The most volatile factor is `Net Margin`.
- Offsetting factor moves occurred in `2021-2022`.

Five-period summary:

- `Revenue` was positive in `5 of 5` periods.
- `Net Margin` was positive in `4 of 5` periods.
- `Share Count` was positive in `5 of 5` periods.

## 4. Correlation And Relationships

- The correlation between revenue growth and net-margin change across the full `2001-2025` year-over-year history is `0.5192`.
- That suggests a moderate positive relationship rather than independence.
- In the top-quartile revenue-growth periods, net margin expanded in `4` periods and contracted in `2`.
- When net margin contracted, EPS still rose in `6` periods.
- In all `6` of those periods, revenue contribution alone outweighed the combined drag from margin and shares.
- In periods with falling share count, the buyback-related EPS lift aligns more strongly with `Revenue` than with `Net Margin`.

---


## Testing Status

Every phase was tested after completion.

### Phase 1 tests

- Replication against the formulas sheet passed.

### Phase 2 tests

- Window row counts passed.
- The original formulas-sheet sample still tied out inside the expanded script.

### Phase 3 tests

- The annual identity `EPS = Revenue x Net Margin / Shares` passed.
- The exact three-factor decomposition tied out perfectly.

### Phase 4 tests

- Two-factor year-over-year tie-out passed.
- Three-factor ranking completeness passed.
- Rolling-window period checks passed.

Overall status:

- All validation checks passed.

---

## Key Caveat

The biggest caution in this analysis is the apparent `Share Count` basis break around `2014`.

This matters because:

- long-history results that involve share count can be distorted
- the `2013-2014` result is not likely a clean operating signal
- conclusions from `2001-2025` should be reviewed with split normalization in mind

Short version:

- `2015-2025` is the cleanest range
- `2010-2025` is usable with care
- `2001-2025` is useful directionally, but share-related conclusions should be caveated until the older share series is normalized

---

## Recommended Next Step

The next best deliverable is a polished presentation-ready summary that:

- focuses on `2015-2025` as the clean core analysis
- uses `2010-2025` as supporting context
- treats `2001-2025` as long-history context with a share-basis caveat
- includes 3 to 5 charts for EPS drivers, rolling contributions, and key turning points

---

## Core Output Files

- `outputs/phase1/phase1_eps_replication_summary_2015_2020.md`
- `outputs/phase2/phase2_eps_summary.md`
- `outputs/phase3/phase3_eps_summary.md`
- `outputs/phase4/phase4_eps_business_answers.md`
- `outputs/phase4/phase4_eps_two_factor_yoy.csv`
- `outputs/phase4/phase4_eps_year_over_year_analysis.csv`

This file is the manager-ready summary of the full workflow and results.
