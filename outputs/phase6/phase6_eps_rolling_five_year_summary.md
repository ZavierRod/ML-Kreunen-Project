# Phase 6 Rolling Five-Year CAGR Summary

## What this does

- Slides a 5-year window across the full 2001-2025 history, shifting by 1 calendar year.
- Reports endpoint levels and per-factor CAGR for each rolling slot.
- Matches the breakdown style Connor described: take the 5-year factor change and annualize it.

## Slot definition

- First slot: `2001-2006`
- Last slot: `2020-2025`
- Total rolling slots: `20` (each slot spans exactly 5 years)

CAGR per factor is computed as:

```text
CAGR = (end_value / start_value) ^ (1 / 5) - 1
```

## Testing

All Phase 6 validation checks passed.

## Rolling 5-year CAGR

| Slot | Revenue CAGR | Net Margin CAGR | Rev/S CAGR | Shares CAGR | EPS CAGR |
| --- | --- | --- | --- | --- | --- |
| 2001-2006 | 161.68% | 29.13% | 136.53% | 10.63% | 205.44% |
| 2002-2007 | 106.73% | 2.24% | 92.37% | 7.46% | 96.68% |
| 2003-2008 | 71.57% | 21.89% | 64.42% | 4.35% | 100.42% |
| 2004-2009 | 49.29% | 17.11% | 44.65% | 3.21% | 69.41% |
| 2005-2010 | 36.72% | 3.97% | 33.95% | 2.06% | 39.28% |
| 2006-2011 | 29.01% | -2.41% | 27.59% | 1.12% | 24.52% |
| 2007-2012 | 24.77% | -3.32% | 23.54% | 1.00% | 19.44% |
| 2008-2013 | 20.56% | 3.41% | 19.01% | 1.31% | 23.07% |
| 2009-2014 | 22.78% | -4.92% | 21.38% | 1.16% | 15.40% |
| 2010-2015 | 20.66% | -5.55% | 19.00% | 1.40% | 12.39% |
| 2011-2016 | 18.95% | -3.43% | 17.40% | 1.32% | 13.38% |
| 2012-2017 | 17.18% | -11.80% | 15.94% | 1.07% | 2.26% |
| 2013-2018 | 19.77% | -0.41% | 18.88% | 0.75% | 18.39% |
| 2014-2019 | 19.65% | -0.19% | 18.89% | 0.64% | 18.67% |
| 2015-2020 | 19.47% | 0.24% | 19.68% | -0.17% | 19.96% |
| 2016-2021 | 23.34% | 6.46% | 24.09% | -0.61% | 32.11% |
| 2017-2022 | 20.60% | 13.17% | 22.14% | -1.26% | 38.23% |
| 2018-2023 | 17.57% | 1.34% | 19.96% | -1.99% | 21.56% |
| 2019-2024 | 16.68% | 6.16% | 19.41% | -2.28% | 26.76% |
| 2020-2025 | 17.15% | 8.26% | 19.92% | -2.30% | 29.82% |

## Notes

- Slots overlap by 4 calendar years, so CAGR values cannot be summed or averaged across slots.
- This is an annualized growth view, not a log decomposition. For factor contribution math that ties out exactly to EPS log change, use the Phase 5 output.
- `shares_cagr` is the raw CAGR of share count - negative values correspond to net buybacks over the slot.
- Diluted shares are on a consistent split-adjusted basis (pre-split 2001-2013 restated x20), so slots that straddle 2013-2014 no longer carry a spurious share-count jump.

## Output files

- `outputs/phase6/phase6_eps_rolling_five_year_cagr.csv`
- `outputs/phase6/phase6_eps_rolling_five_year_validation.csv`
- `outputs/phase6/phase6_eps_rolling_five_year_summary.md`

## Column reference for `phase6_eps_rolling_five_year_cagr.csv`

Every row in the CSV is one rolling 5-year slot. The columns below are listed in the exact order they appear in the file, with the formula used for each one. All `*_start` and `*_end` columns are read directly from the matching year in [outputs/phase3/phase3_eps_annual_tables.csv](outputs/phase3/phase3_eps_annual_tables.csv) for the `2001_2025` window.

### Slot identifiers

- `slot`: Human-readable label for the rolling window, formatted as `start_year-end_year` (for example `2015-2020`).
- `start_year`: First calendar year of the slot. The value of every `*_start` column is read from this year.
- `end_year`: Last calendar year of the slot. The value of every `*_end` column is read from this year. Equal to `start_year + 5`.
- `years_in_slot`: Number of years between the endpoints. Always `5` in Phase 6 and used as the CAGR denominator.

### Revenue columns

- `revenue_start`: Total Gross revenue (GAAP) in `start_year`, in millions USD.
- `revenue_end`: Total Gross revenue (GAAP) in `end_year`, in millions USD.
- `revenue_total_growth`: Cumulative 5-year change, computed as `revenue_end / revenue_start - 1`. Expressed as a decimal (0.25 means +25%).
- `revenue_cagr`: Annualized growth rate, computed as `(revenue_end / revenue_start) ** (1 / 5) - 1`. This is Connor's example-style CAGR applied to revenue.

### Net income columns

- `net_income_start`: Net income, reported in `start_year`, in millions USD.
- `net_income_end`: Net income, reported in `end_year`, in millions USD.
- `net_income_cagr`: Annualized growth rate, computed as `(net_income_end / net_income_start) ** (1 / 5) - 1`.

### Share count columns

- `shares_start`: Average diluted shares in `start_year`, in millions.
- `shares_end`: Average diluted shares in `end_year`, in millions.
- `shares_cagr`: Annualized change in share count, computed as `(shares_end / shares_start) ** (1 / 5) - 1`. A negative value means the share count shrank on average each year (net buybacks); a positive value means dilution.

### Net margin columns

- `net_margin_start`: Net margin in `start_year`, computed upstream in Phase 3 as `net_income / revenue`. Expressed as a decimal (0.22 means 22%).
- `net_margin_end`: Net margin in `end_year`, same formula.
- `net_margin_cagr`: Annualized change in the margin ratio, computed as `(net_margin_end / net_margin_start) ** (1 / 5) - 1`. Because net margin is already a ratio, this reads as the annualized percentage change in the margin itself, not a new margin value.

### Revenue per share columns

- `rev_per_share_start`: Revenue per average diluted share in `start_year`, computed upstream as `revenue / average_diluted_shares`.
- `rev_per_share_end`: Same formula for `end_year`.
- `rev_per_share_cagr`: Annualized growth, computed as `(rev_per_share_end / rev_per_share_start) ** (1 / 5) - 1`.

### EPS columns

- `eps_start`: Earnings per diluted share in `start_year`, computed upstream as `net_income / average_diluted_shares`.
- `eps_end`: Same formula for `end_year`.
- `eps_total_growth`: Cumulative 5-year change in EPS, computed as `eps_end / eps_start - 1`.
- `eps_cagr`: Annualized EPS growth, computed as `(eps_end / eps_start) ** (1 / 5) - 1`. This is the headline number for the slot.

### How the CAGR is computed

Every `*_cagr` column in the file uses the same helper in [scripts/phase6_eps_rolling_five_year_cagr.py](scripts/phase6_eps_rolling_five_year_cagr.py):

```python
def cagr(end_value: float, start_value: float, years: int) -> float:
    return (end_value / start_value) ** (1 / years) - 1
```

`years` is always `5` for Phase 6. The validation CSV re-runs this formula against each `*_start` / `*_end` pair and confirms it matches the stored `*_cagr` column with zero gap.
