# Phase 5 Five-Year Slot Summary

## What this does

- Collapses the long history into non-overlapping 5-year slots.
- Reports slot-level totals, endpoint-to-endpoint growth, and CAGR.
- Applies the same log-based 2-factor and 3-factor bridges used in Phase 4.
- Keeps the drill-down year-over-year rows so each slot can be expanded.

## Slot definition

- `2015_2025`: 2015-2020, 2020-2025
- `2010_2025`: 2010-2015, 2015-2020, 2020-2025
- `2001_2025`: 2001-2005, 2005-2010, 2010-2015, 2015-2020, 2020-2025

The `2001-2005` slot covers 4 calendar years because 2001 is not on the 5-year grid.
All other slots are exact 5-year spans.

## Testing

All Phase 5 validation checks passed.

### 2015_2025

| Slot | Revenue CAGR | EPS CAGR | Rev/S Contribution | Net Margin Contribution | Share Count Contribution | EPS Log Change | Largest Driver | Direction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2015-2020 | 19.47% | 19.96% | 0.8981 | 0.0119 | 0.0086 | 0.9100 | revenue | positive |
| 2020-2025 | 17.15% | 29.82% | 0.9081 | 0.3969 | 0.1165 | 1.3050 | revenue | positive |

### 2010_2025

| Slot | Revenue CAGR | EPS CAGR | Rev/S Contribution | Net Margin Contribution | Share Count Contribution | EPS Log Change | Largest Driver | Direction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2010-2015 | 20.66% | 12.39% | 0.8697 | -0.2856 | -0.0694 | 0.5841 | revenue | positive |
| 2015-2020 | 19.47% | 19.96% | 0.8981 | 0.0119 | 0.0086 | 0.9100 | revenue | positive |
| 2020-2025 | 17.15% | 29.82% | 0.9081 | 0.3969 | 0.1165 | 1.3050 | revenue | positive |

### 2001_2025

| Slot | Revenue CAGR | EPS CAGR | Rev/S Contribution | Net Margin Contribution | Share Count Contribution | EPS Log Change | Largest Driver | Direction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2001-2005 | 190.31% | 240.39% | 3.8166 | 1.0831 | -0.4464 | 4.8997 | revenue | positive |
| 2005-2010 | 36.72% | 39.28% | 1.4616 | 0.1948 | -0.1021 | 1.6564 | revenue | positive |
| 2010-2015 | 20.66% | 12.39% | 0.8697 | -0.2856 | -0.0694 | 0.5841 | revenue | positive |
| 2015-2020 | 19.47% | 19.96% | 0.8981 | 0.0119 | 0.0086 | 0.9100 | revenue | positive |
| 2020-2025 | 17.15% | 29.82% | 0.9081 | 0.3969 | 0.1165 | 1.3050 | revenue | positive |

## Notes

- Positive log contribution = that factor helped EPS in the slot.
- Negative log contribution = that factor hurt EPS in the slot.
- `share_count` is signed so buybacks read as positive.
- Diluted shares are on a consistent split-adjusted basis (pre-split 2001-2013 restated x20), so the old 2013-2014 break no longer distorts the `2010-2015` slot.
- Adjacent slots share one endpoint year so the log contributions connect cleanly; as a result, `revenue_total_in_slot` and `net_income_total_in_slot` double-count that endpoint if summed across slots.
- Use the breakdown CSV for the year-by-year view that sums to each slot total.

## Output files

- `outputs/phase5/phase5_eps_five_year_slots.csv`
- `outputs/phase5/phase5_eps_five_year_slot_breakdown.csv`
- `outputs/phase5/phase5_eps_five_year_slots_validation.csv`
- `outputs/phase5/phase5_eps_five_year_slots_summary.md`
