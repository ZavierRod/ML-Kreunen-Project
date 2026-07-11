# Phase 10 Enterprise Value & C-Return Summary

## Testing

All Phase 10 validation checks passed.

Validation file: `outputs/phase10/phase10_validation_results.csv`

## Method

- Builds on Phase 9 levels (`outputs/phase9/phase9_factor_levels.csv`); no new data pull.
- All deltas are SIMPLE year-over-year percent change, `level_t / level_t-1 - 1` (same as Phase 9).
- EV is a per-share level: `EV = Price - NetCash/share`, where `NetCash/share = NetCash_total / diluted Shares`.
- `eff.dCash = dEV - dPrice` (isolates the cash contribution to the value move).
- `C-Return = dFCF - eff.dCash`, using total Free Cash Flow simple percent change (same FCF basis as Phase 9).
- EV depends on Price, so the panel starts with the 2004-2005 period (GOOG IPO 2004).
- Reported as a standalone EV panel, NOT folded into the Phase 9 seven-factor ranking/weights.

## Summary - Full History (2004-2025)

| Rank | Metric | Mean |%| | Mean % | Up | Down |
| --- | --- | --- | --- | --- | --- |
| 1 | EV_pct_change | 42.3% | 30.6% | 15 | 6 |
| 2 | FCF_pct_change | 35.5% | 30.6% | 16 | 5 |
| 3 | c_return | 34.7% | 29.4% | 15 | 6 |
| 4 | eff_delta_cash | 4.3% | 1.2% | 12 | 9 |

## Summary - Recent 5 Years (2020-2025)

| Rank | Metric | Mean |%| | Mean % | Up | Down |
| --- | --- | --- | --- | --- | --- |
| 1 | EV_pct_change | 57.2% | 40.8% | 4 | 1 |
| 2 | FCF_pct_change | 17.6% | 13.4% | 4 | 1 |
| 3 | c_return | 13.8% | 9.9% | 3 | 2 |
| 4 | eff_delta_cash | 4.4% | 3.6% | 4 | 1 |

## Combined Ranking with Phase 9 Factors

The Phase 9 factors and the new EV metrics ranked together by average size of move (`mean_abs`). This is a comparison of movers only: there is deliberately NO weight column, because EV, eff.dCash, and C-Return are derived from Price, NetCash, and FCF, so folding them into the Phase 9 share-of-movement weighting would double-count. FCF appears once (as the Phase 9 factor). `type` flags each row as `factor`, `derived-level` (EV), or `derived-delta` (eff.dCash, C-Return).

Both windows are recomputed on a shared basis so the numbers are directly comparable. Full history is aligned to 2004-2025 (EV needs Price, which starts 2004), so these Phase 9 numbers differ from the Phase 9 2001-2025 tables by design.

### Combined - Full History (2004-2025)

| Rank | Metric | Type | Mean |%| | Mean % | Up | Down |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | EPS | factor | 45.6% | 40.4% | 19 | 2 |
| 2 | EV | derived-level | 42.3% | 30.6% | 15 | 6 |
| 3 | Price | factor | 39.4% | 29.3% | 16 | 5 |
| 4 | FCF | factor | 35.5% | 30.6% | 16 | 5 |
| 5 | C-Return | derived-delta | 34.7% | 29.4% | 15 | 6 |
| 6 | NetCash | factor | 31.3% | 29.3% | 18 | 3 |
| 7 | Revenue | factor | 27.5% | 27.5% | 21 | 0 |
| 8 | Net Margin | factor | 23.9% | 9.4% | 12 | 9 |
| 9 | eff.dCash | derived-delta | 4.3% | 1.2% | 12 | 9 |
| 10 | Shares | factor | 1.9% | 0.6% | 13 | 8 |

### Combined - Recent 5 Years (2020-2025)

| Rank | Metric | Type | Mean |%| | Mean % | Up | Down |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | EV | derived-level | 57.2% | 40.8% | 4 | 1 |
| 2 | Price | factor | 52.7% | 37.3% | 4 | 1 |
| 3 | EPS | factor | 42.1% | 34.6% | 4 | 1 |
| 4 | Net Margin | factor | 21.8% | 10.5% | 4 | 1 |
| 5 | Revenue | factor | 17.7% | 17.7% | 5 | 0 |
| 6 | FCF | factor | 17.6% | 13.4% | 4 | 1 |
| 7 | C-Return | derived-delta | 13.8% | 9.9% | 3 | 2 |
| 8 | NetCash | factor | 10.1% | 1.5% | 2 | 3 |
| 9 | eff.dCash | derived-delta | 4.4% | 3.6% | 4 | 1 |
| 10 | Shares | factor | 2.3% | -2.3% | 0 | 5 |

## Output Files

- `outputs/phase10/phase10_ev_levels.csv`
- `outputs/phase10/phase10_ev_c_return_panel.csv`
- `outputs/phase10/phase10_ev_c_return_summary_full_2004_2025.csv`
- `outputs/phase10/phase10_ev_c_return_summary_recent5_2020_2025.csv`
- `outputs/phase10/phase10_combined_ranking_full_2004_2025.csv`
- `outputs/phase10/phase10_combined_ranking_recent5_2020_2025.csv`
- `outputs/phase10/phase10_validation_results.csv`
- `outputs/phase10/presentation_tables/table13_ev_c_return_summary_full_2004-2025.csv`
- `outputs/phase10/presentation_tables/table14_ev_c_return_summary_recent5_2020-2025.csv`
- `outputs/phase10/presentation_tables/table15_combined_ranking_full_2004-2025.csv`
- `outputs/phase10/presentation_tables/table16_combined_ranking_recent5_2020-2025.csv`
