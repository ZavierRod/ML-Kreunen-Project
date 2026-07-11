# Phase 9 Seven-Factor Ranking Summary

## Testing

All Phase 9 validation checks passed.

Validation file: `outputs/phase9/phase9_validation_results.csv`

## Method

- Factors ranked: Revenue, Net Margin, EPS, FCF, NetCash, Shares, Price.
- Builds on Phase 8 by adding Price from Yahoo Finance.
- Each factor's year-over-year SIMPLE percent change is computed per period.
- Per-period weight = `|pct change_i| / sum_j |pct change_j|` over factors with valid data (positive, sum to 100%).
- Factors are ranked by mean absolute percent change.
- NetCash = Cash + Marketable securities + Non-marketable equity securities - Short-term debt - Long-Term Debt (matches the workbook NCash/Share row).
- Diluted shares are split-consistent (pre-split 2001-2013 restated x20).
- Price = split-adjusted year-end close for `GOOG` from Yahoo Finance, last trading day on or before 12/31, starting 2004.

## Ranking - Full History (2001-2025)

| Rank | Factor | Mean |% change| | Mean weight | Mean % change |
| --- | --- | --- | --- | --- |
| 1 | EPS | 97.0% | 19.7% | 91.8% |
| 2 | NetCash | 85.4% | 15.1% | 83.6% |
| 3 | FCF | 66.1% | 18.1% | 61.8% |
| 4 | Revenue | 55.7% | 16.1% | 55.7% |
| 5 | Price | 39.4% | 21.6% | 29.3% |
| 6 | Net Margin | 34.4% | 11.0% | 16.0% |
| 7 | Shares | 3.4% | 1.1% | 2.2% |

- Largest average mover (2001-2025): `EPS`.

## Ranking - Recent 5 Years (2020-2025)

| Rank | Factor | Mean |% change| | Mean weight | Mean % change |
| --- | --- | --- | --- | --- |
| 1 | Price | 52.7% | 34.3% | 37.3% |
| 2 | EPS | 42.1% | 24.4% | 34.6% |
| 3 | Net Margin | 21.8% | 14.0% | 10.5% |
| 4 | Revenue | 17.7% | 10.0% | 17.7% |
| 5 | FCF | 17.6% | 8.8% | 13.4% |
| 6 | NetCash | 10.1% | 6.8% | 1.5% |
| 7 | Shares | 2.3% | 1.7% | -2.3% |

- Largest average mover (2020-2025): `Price`.

## Output Files

- `outputs/phase9/phase9_factor_levels.csv`
- `outputs/phase9/phase9_seven_factor_panel.csv`
- `outputs/phase9/phase9_seven_factor_ranking_full_2001_2025.csv`
- `outputs/phase9/phase9_seven_factor_ranking_recent5_2020_2025.csv`
- `outputs/phase9/phase9_validation_results.csv`
- `outputs/phase9/presentation_tables/table11_seven_factor_ranking_full_2001-2025.csv`
- `outputs/phase9/presentation_tables/table12_seven_factor_ranking_recent5_2020-2025.csv`
- `data/goog_yahoo_year_end_prices.csv`
