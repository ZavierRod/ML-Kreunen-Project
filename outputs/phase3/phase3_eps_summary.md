# Phase 3 EPS Three-Factor Decomposition Summary

## What this does

- Builds the full year-over-year three-factor EPS decomposition.
- Splits EPS change into Revenue, Net Margin, and Share Count effects.
- Uses exact log contributions so the factor bridge ties out cleanly.
- Adds largest-driver labeling to support the next analysis phase.

## Windows covered

- `2015_2025`: 11 annual rows, 10 year-over-year rows
- `2010_2025`: 16 annual rows, 15 year-over-year rows
- `2001_2025`: 25 annual rows, 24 year-over-year rows

## Testing

- Row counts were validated for each requested window.
- The annual accounting identity `EPS = Revenue x Net Margin / Shares` was tested.
- The exact log decomposition was tested to tie out back to EPS change.
- Share-count directionality was tested so buybacks read as positive EPS support.

## Result

Phase 3 decomposition completed successfully.

The largest exact tie-out gap is `0.000000000000`.
The largest single factor magnitude in the generated output is `1.626367362996` log points.

## Important note

- The `2001-2025` window is fully decomposed, but the older share-count basis still needs business review before drawing strong conclusions across the 2014 break.
- This phase gives you an exact factor bridge for analysis; it does not yet answer the narrative business questions.

## Output files

- `outputs/phase3/phase3_eps_annual_tables.csv`
- `outputs/phase3/phase3_eps_three_factor_decomposition.csv`
- `outputs/phase3/phase3_eps_validation_results.csv`
- `outputs/phase3/phase3_eps_summary.md`
