# Excess-Return Engine

This package is the research foundation for the configurable one-month
excess-return engine. It reads the licensed WRDS-derived panel from a local path;
the data remains outside this Git repository.

## First local build

Use the Python environment in which `requirements.txt` is installed:

```bash
export WRDS_RESEARCH_DATA_DIR="/Users/zavierrodrigues/DatasetKreunenTest"
python -m excess_return_engine.data
```

By default, the command writes these ignored files under
`local_artifacts/excess_return_engine/`:

- `benchmark_returns.parquet`
- `training_panel.parquet`
- `inference_panel.parquet`
- `unresolved_labels.parquet`

The initial research benchmark is the covered universe's monthly return, weighted
by each security's prior-calendar-month market capitalization. Replace this with a
licensed CRSP index return when that series is available.

## Label contract

For a factor observation at month `t`, a label is created only when the same
`PERMNO` has a return at exact calendar month `t + 1` and the benchmark has a return
for that same month:

```text
excess_return_next_month =
    stock_return_next_month - benchmark_return_next_month
```

The legacy `y_next` column is deliberately discarded. Missing or non-contiguous
outcomes remain in `unresolved_labels.parquet` for audit instead of being silently
dropped. The latest unresolved cross-section is also written as the inference
panel.

The existing `monthly_panel.parquet` previously dropped each security's final
observed month when it created `y_next`. Its latest cross-section is therefore a
migration fixture, not yet a production inference panel. The next data milestone is
to rebuild the monthly panel from `final_with_ev.parquet` while retaining every
month, including the latest unlabeled row and final observations around delistings.

This stage also does not resolve the outstanding CRSP delisting-return and
fundamental-availability-date audits documented in the feature plan.
