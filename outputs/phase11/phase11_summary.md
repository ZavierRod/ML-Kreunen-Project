# Phase 11 Effective Shares & Net Margin Summary

## Testing

All Phase 11 validation checks passed.

Validation file: `outputs/phase11/phase11_validation_results.csv`

## Method

- Builds on Phase 9 levels (`outputs/phase9/phase9_factor_levels.csv`); no new data pull.
- All deltas are SIMPLE year-over-year percent change, `level_t / level_t-1 - 1` (same as Phase 9).
- `eff.Shares = (Shares_t-1 / Shares_t - 1) * (1 + dRevenue)`, where dRevenue is the current year's simple percent change in total Revenue.
- `eff.NetMargin = (Net Margin_t / Net Margin_t-1 - 1) * (1 + dRevPerShare)`, where dRevPerShare is the current year's simple percent change in Revenue per share.
- Revenue per share = total Revenue / diluted Shares.
- Full history covers 2001-2025 (24 year-over-year periods).
- Reported as a standalone effective-change panel, NOT folded into the Phase 9 seven-factor weights.

## Summary - Full History (2001-2025)

| Rank | Metric | Mean |%| | Mean % | Up | Down |
| --- | --- | --- | --- | --- | --- |
| 1 | eff.NetMargin | 75.1% | 42.8% | 14 | 10 |
| 2 | eff.Shares | 8.0% | -6.7% | 8 | 16 |

## Summary - Recent 5 Years (2020-2025)

| Rank | Metric | Mean |%| | Mean % | Up | Down |
| --- | --- | --- | --- | --- | --- |
| 1 | eff.NetMargin | 26.9% | 14.2% | 4 | 1 |
| 2 | eff.Shares | 2.7% | 2.7% | 5 | 0 |

## Combined Ranking with Phase 9 Factors

The Phase 9 factors and the new effective metrics ranked together by average size of move (`mean_abs`). This is a comparison of movers only: there is deliberately NO weight column, because eff.Shares and eff.NetMargin are derived from Shares, Revenue, Net Margin, and Rev/Share, so folding them into the Phase 9 share-of-movement weighting would double-count. `type` flags each row as `factor` or `derived-effective`.

### Combined - Full History (2001-2025)

| Rank | Metric | Type | Mean |%| | Mean % | Up | Down |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | EPS | factor | 97.0% | 91.8% | 21 | 3 |
| 2 | NetCash | factor | 85.4% | 83.6% | 21 | 3 |
| 3 | eff.NetMargin | derived-effective | 75.1% | 42.8% | 14 | 10 |
| 4 | FCF | factor | 66.1% | 61.8% | 19 | 5 |
| 5 | Revenue | factor | 55.7% | 55.7% | 24 | 0 |
| 6 | Price | factor | 39.4% | 29.3% | 16 | 5 |
| 7 | Net Margin | factor | 34.4% | 16.0% | 14 | 10 |
| 8 | eff.Shares | derived-effective | 8.0% | -6.7% | 8 | 16 |
| 9 | Shares | factor | 3.4% | 2.2% | 16 | 8 |

### Combined - Recent 5 Years (2020-2025)

| Rank | Metric | Type | Mean |%| | Mean % | Up | Down |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Price | factor | 52.7% | 37.3% | 4 | 1 |
| 2 | EPS | factor | 42.1% | 34.6% | 4 | 1 |
| 3 | eff.NetMargin | derived-effective | 26.9% | 14.2% | 4 | 1 |
| 4 | Net Margin | factor | 21.8% | 10.5% | 4 | 1 |
| 5 | Revenue | factor | 17.7% | 17.7% | 5 | 0 |
| 6 | FCF | factor | 17.6% | 13.4% | 4 | 1 |
| 7 | NetCash | factor | 10.1% | 1.5% | 2 | 3 |
| 8 | eff.Shares | derived-effective | 2.7% | 2.7% | 5 | 0 |
| 9 | Shares | factor | 2.3% | -2.3% | 0 | 5 |

## Output Files

- `outputs/phase11/phase11_factor_levels.csv`
- `outputs/phase11/phase11_effective_panel.csv`
- `outputs/phase11/phase11_effective_summary_full_2001_2025.csv`
- `outputs/phase11/phase11_effective_summary_recent5_2020_2025.csv`
- `outputs/phase11/phase11_combined_ranking_full_2001_2025.csv`
- `outputs/phase11/phase11_combined_ranking_recent5_2020_2025.csv`
- `outputs/phase11/phase11_validation_results.csv`
- `outputs/phase11/presentation_tables/table17_effective_summary_full_2001-2025.csv`
- `outputs/phase11/presentation_tables/table18_effective_summary_recent5_2020-2025.csv`
- `outputs/phase11/presentation_tables/table19_combined_ranking_full_2001-2025.csv`
- `outputs/phase11/presentation_tables/table20_combined_ranking_recent5_2020-2025.csv`
