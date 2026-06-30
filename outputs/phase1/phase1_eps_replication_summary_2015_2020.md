# Phase 1 EPS Replication Summary

## What this does

- Rebuilds the 2015-2020 annual EPS driver table from `Model.csv`.
- Recreates the same base-year horizon metrics shown in `Sheet1.csv`.
- Compares the calculated results against the formulas sheet values.

## Result

The replication works.

The calculated `∆Rev/Share`, `∆NetMargin`, and sheet-style `∆EPS` match the formulas sheet values for 2015-2020.
The formulas sheet is using `2015` as the base year and annualizing each horizon, rather than using adjacent year-over-year changes.
It is also treating `∆EPS` as an additive approximation, not as the true EPS CAGR.

That additive relationship is close, but not exact, because EPS is multiplicative:

```text
EPS = Rev/S x Net Margin
```

The largest difference versus the formulas sheet is `0.000000000000`.
The largest gap between the sheet-style approximation and the true EPS CAGR is `0.057679258163`.

## Output files

- `outputs/phase1/phase1_eps_annual_table_2015_2020.csv`
- `outputs/phase1/phase1_eps_replication_check_2015_2020.csv`
- `outputs/phase1/phase1_eps_replication_summary_2015_2020.md`

## Notes

- This completes Phase 1 only.
- The next step is to extend the same methodology through 2025 before moving to the 3-factor decomposition.
