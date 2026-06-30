# Phase 2 EPS Expansion Summary

## What this does

- Expands the formulas-sheet methodology to the requested longer windows.
- Rebuilds annual tables for `2015-2025`, `2010-2025`, and `2001-2025`.
- Exports the base-year horizon results for each window.
- Writes explicit validation results so Phase 2 is test-backed.

## Windows covered

- `2015_2025`: 11 annual rows, 10 horizon rows
- `2010_2025`: 16 annual rows, 15 horizon rows
- `2001_2025`: 25 annual rows, 24 horizon rows

## Testing

- The Phase 1 formulas-sheet sample still ties out inside the Phase 2 script.
- Row counts were validated for each requested window.
- All generated horizon values were checked for finite numeric output.

## Result

Phase 2 expansion completed successfully.

The largest gap between the sheet-style approximation and true EPS CAGR is `5.967268068191`.

## Important note

- The `2001-2025` window mechanically expands correctly, but the older share series still needs business review because of the share-basis jump around 2014.
- This phase is an exact methodology expansion, not yet a share-normalization cleanup.

## Output files

- `outputs/phase2/phase2_eps_annual_tables.csv`
- `outputs/phase2/phase2_eps_horizon_expansion.csv`
- `outputs/phase2/phase2_eps_validation_results.csv`
- `outputs/phase2/phase2_eps_summary.md`
