# Phase 4 EPS Business Analysis

## Testing

All Phase 4 validation checks passed.

Validation file:
- `outputs/phase4/phase4_eps_validation_results.csv`

## Replication And Expansion

The exact year-over-year two-factor bridge is exported in `outputs/phase4/phase4_eps_two_factor_yoy.csv`.
For each requested window, that file shows how `Rev/S` and `Net Margin` contributed to EPS movement for every adjacent year pair.

The enriched three-factor year-over-year file is `outputs/phase4/phase4_eps_year_over_year_analysis.csv`.
It adds factor ranks, direction labels, and offset flags for each period.

## Year-Over-Year Decomposition

The single largest factor swing in the full `2001-2025` output is `revenue` in `2001-2002`, and it is `positive`.
Diluted shares are now on a consistent split-adjusted basis (pre-split 2001-2013 restated x20), so this swing is no longer distorted by the old data break.

## Five-Year Rolling Analysis

Using the `2020-2025` year-over-year periods, the most consistent positive contributor is `revenue`.
The most volatile factor over the same periods is `net_margin`.
Offsetting factor moves occurred in: `2021-2022`.

Five-year rolling factor stats:
- `revenue`: positive in 5 of 5 periods, stdev `0.1069`
- `net_margin`: positive in 4 of 5 periods, stdev `0.2384`
- `share_count`: positive in 5 of 5 periods, stdev `0.0083`

## Correlation And Relationships

Across the full `2001-2025` year-over-year dataset, the correlation between revenue growth and net-margin change is `0.5192`.
For the top-quartile revenue-growth years (threshold `0.4498`), net margin expanded in `4` periods, contracted in `2`, and was flat in `0`.

When net margin contracted, EPS still rose in `7` periods.
In `7` of those periods, revenue contribution alone outweighed the combined drag from margin and shares.

For years with falling share count, the buyback contribution correlates `-0.5043` with revenue contribution and `-0.0468` with net-margin contribution.
That means the share-count lift aligns more strongly with revenue than margin.

## Output Files

- `outputs/phase4/phase4_eps_two_factor_yoy.csv`
- `outputs/phase4/phase4_eps_year_over_year_analysis.csv`
- `outputs/phase4/phase4_eps_validation_results.csv`
- `outputs/phase4/phase4_eps_business_answers.md`

## Important Note

- The pre-split 2001-2013 diluted-share counts have been restated x20, so the share series is consistent across the full history.
- The Phase 4 answers are mechanically correct and long-run share-count conclusions no longer require a split-normalization caveat.
