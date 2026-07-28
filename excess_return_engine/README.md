# Excess-Return Engine

This package is the research foundation for the configurable one-month
excess-return engine. It reads the licensed WRDS-derived panel from a local path;
the data remains outside this Git repository.

## First local build

Use the Python environment in which `requirements.txt` is installed:

```bash
export WRDS_RESEARCH_DATA_DIR="/Users/zavierrodrigues/DatasetKreunenTest"
python -m excess_return_engine.monthly \
  --daily-path "$WRDS_RESEARCH_DATA_DIR/final_with_ev.parquet"

python -m excess_return_engine.data \
  --data-dir local_artifacts/excess_return_engine/monthly_panel_full.parquet
```

By default, the command writes these ignored files under
`local_artifacts/excess_return_engine/`:

- `monthly_panel_full.parquet`
- `feature_panel.parquet`
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

The new monthly builder reads `final_with_ev.parquet` one row group at a time and
retains every observed month, including each security's final unlabeled row. The
older `monthly_panel.parquet` remains a migration fixture because its legacy
`y_next` build dropped those final observations.

This stage also does not resolve the outstanding CRSP delisting-return and
fundamental-availability-date audits documented in the feature plan.

## Run a configurable forecast

The factor panel currently exposes 14 versioned factors:

```text
momentum_12_1
volatility_21d
liquidity_21d
asset_growth
leverage
profit_margin
roe
ev_ebitda
size
book_to_market
return_1m
momentum_6_1
turnover
relative_volatility
```

Run an Elastic Net forecast by permanent security ID and selected factors:

```bash
OMP_NUM_THREADS=1 \
OPENBLAS_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 \
python -m excess_return_engine.model \
  --permno 90319 \
  --factors momentum_12_1 volatility_21d asset_growth leverage \
            profit_margin roe ev_ebitda size
```

The command prints and saves:

- Expected one-month excess return
- Probability of a positive excess return
- Empirical 80% prediction interval
- Factor-level contributions and normalized values
- Chronological holdout metrics
- Selected hyperparameters
- Data, target, feature, and model versions

Hyperparameters are selected on a chronological tuning window. Residual
probabilities and intervals use a later calibration window, and interval coverage is
measured on the final half of that window. The final selected model is then fit on
all historical rows before forecasting the requested security.

Forecasts are research outputs. The current benchmark is the lagged-cap-weighted
covered universe, fundamentals use the documented availability-lag proxy, and
explicit CRSP delisting returns are still pending an additional source extract.
