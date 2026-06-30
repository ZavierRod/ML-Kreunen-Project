# Phase 8 Six-Factor Ranking Summary

## Testing

All Phase 8 validation checks passed.

Validation file: `outputs/phase8/phase8_validation_results.csv`

## Method

- Factors ranked: Revenue, Net Margin, EPS, FCF, NetCash, Shares.
- Each factor's year-over-year SIMPLE percent change is computed per period.
- Per-period weight = `|pct change_i| / sum_j |pct change_j|` (positive, sum to 100%).
- Factors are ranked by mean absolute percent change.
- NetCash = Cash + Marketable securities + Non-marketable equity securities - Short-term debt - Long-Term Debt (matches the workbook NCash/Share row).
- Diluted shares are split-consistent (pre-split 2001-2013 restated x20).

## Ranking - Full History (2001-2025)

| Rank | Factor | Mean |% change| | Mean weight | Mean % change |
| --- | --- | --- | --- | --- |
| 1 | EPS | 97.0% | 24.5% | 91.8% |
| 2 | NetCash | 85.4% | 18.1% | 83.6% |
| 3 | FCF | 66.1% | 22.7% | 61.8% |
| 4 | Revenue | 55.7% | 19.3% | 55.7% |
| 5 | Net Margin | 34.4% | 13.9% | 16.0% |
| 6 | Shares | 3.4% | 1.5% | 2.2% |

- Largest average mover (2001-2025): `EPS`.

## Ranking - Recent 5 Years (2020-2025)

| Rank | Factor | Mean |% change| | Mean weight | Mean % change |
| --- | --- | --- | --- | --- |
| 1 | EPS | 42.1% | 37.3% | 34.6% |
| 2 | Net Margin | 21.8% | 21.2% | 10.5% |
| 3 | Revenue | 17.7% | 15.1% | 17.7% |
| 4 | FCF | 17.6% | 13.2% | 13.4% |
| 5 | NetCash | 10.1% | 10.6% | 1.5% |
| 6 | Shares | 2.3% | 2.7% | -2.3% |

- Largest average mover (2020-2025): `EPS`.

## Output Files

- `outputs/phase8/phase8_factor_levels.csv`
- `outputs/phase8/phase8_six_factor_panel.csv`
- `outputs/phase8/phase8_six_factor_ranking_full_2001_2025.csv`
- `outputs/phase8/phase8_six_factor_ranking_recent5_2020_2025.csv`
- `outputs/phase8/phase8_validation_results.csv`
- `outputs/phase8/presentation_tables/table9_six_factor_ranking_full_2001-2025.csv`
- `outputs/phase8/presentation_tables/table10_six_factor_ranking_recent5_2020-2025.csv`
