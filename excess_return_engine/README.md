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

Use a trailing training window when the research question should emphasize more
recent regimes:

```bash
python -m excess_return_engine.model \
  --permno 90319 \
  --factors momentum_12_1 volatility_21d asset_growth leverage \
  --training-window-months 120
```

The window is measured in distinct calendar months immediately before the as-of
date. It must leave enough history for the 60-month minimum fit, 12-month tuning,
and 48-month calibration/evaluation splits. The default remains all eligible
history. The requested window is part of the configuration ID and model record, so
otherwise identical 10-year and expanding-history forecasts are separate runs.

The command prints and saves:

- Expected one-month excess return
- Probability of a positive excess return
- Empirical 80% prediction interval
- Factor-level contributions and normalized values
- Current percentile regime for every selected factor
- Nearest historical conditions and their realized excess-return distribution
- Transparent model-reliability and data-quality scores with component evidence
- Chronological holdout metrics
- Selected hyperparameters
- Data, target, feature, and model versions

Hyperparameters are selected on a chronological tuning window. Residual
probabilities and intervals use a later calibration window, and interval coverage is
measured on the final half of that window. The final selected model is then fit on
all historical rows before forecasting the requested security.

The default 48-month calibration window uses its first 24 months to estimate the
residual distribution and leaves its final 24 months untouched for validation. The
forecast record includes ten equal-count probability-calibration bins and
outcome-year MAE, RMSE, direction, interval coverage, and actual-versus-predicted
excess-return summaries.

## Reliability assessment

`excess_return_engine/reliability.py` calculates a versioned model-reliability score
from six measurable components:

- Out-of-sample R-squared versus a zero-excess-return baseline
- Brier skill versus the calibration-window constant-probability baseline
- Prediction-interval coverage error
- Stability between pre-calibration and final Elastic Net coefficients
- Similarity to the nearest historical normalized factor vector
- Number of close historical analogs

The separate data-quality score uses current factor completeness, historical factor
coverage, training depth, and point-in-time status. Research-lag-proxy fundamentals
cap that score below `High` until actual availability timestamps are integrated.

The assessment also reports the current vector's multivariate training-distance
percentile and selected-factor pairs with absolute historical correlation of at
least `0.85`. Failed baseline comparisons, poor interval coverage, distribution
shift, sparse analog coverage, correlation, and point-in-time limitations remain
explicit warnings in the forecast JSON and UI.

Forecasts are research outputs. The current benchmark is the lagged-cap-weighted
covered universe, fundamentals use the documented availability-lag proxy, and
explicit CRSP delisting returns are still pending an additional source extract.

## Run the local research UI

The Streamlit workflow reads the ignored research panels from
`local_artifacts/excess_return_engine/` by default:

```bash
OMP_NUM_THREADS=1 \
OPENBLAS_NUM_THREADS=1 \
VECLIB_MAXIMUM_THREADS=1 \
python -m streamlit run ui/excess_return_engine/app.py
```

Set `EXCESS_RETURN_ARTIFACT_DIR` to use a different local panel directory. The UI
supports permanent-security company selection, factor presets and custom factor
sets, configurable prediction intervals, pre-run data-quality gates, contribution
attribution, current factor regimes, historical analog outcomes, validation
metrics, version metadata, saved experiment comparison, and JSON export.

This research UI is intentionally separate from the public Streamlit deployment.
The licensed WRDS-derived panels remain local and must not be committed to Git or
bundled into a public application.

## Saved experiments

After generating a forecast, save it as a named experiment from the local UI. A
saved experiment contains the configuration and compact forecast summary needed to
restore and compare a run:

- Permanent security ID, display ticker, company name, and as-of date
- Selected factor IDs, training window, interval level, target, and benchmark
- Expected excess return, positive-return probability, interval, and quality scores
- Factor contributions and model, feature, target, and data version IDs

Saved manifests are versioned JSON files under the ignored
`local_artifacts/excess_return_engine/experiments/` directory. They do not contain
raw panel rows, historical analog rows, credentials, or licensed source data.
Saving the same name and configuration is idempotent.

The comparison workspace displays return and probability deltas relative to the
first selected experiment, grouped factor contributions, and a downloadable CSV.
It warns when selected experiments differ in security, as-of date, target,
benchmark, or data version so comparisons are not presented as equivalent when
their underlying contracts differ.

Applying a saved configuration restores its company, factor set, and prediction
interval, including the training window. Version 1 experiment manifests load as
all-available-history configurations; new saves use version 2. The current research
UI can restore only an as-of date present in the loaded inference snapshot; older
snapshots must first be loaded through `EXCESS_RETURN_ARTIFACT_DIR`.

## Ask the Forecast

After generating a forecast, the local UI can send a question and that run's
structured evidence to the OpenAI Responses API. Numerical forecasts always come
from the quantitative engine; the LLM receives no training or inference panel and
is limited to explaining the immutable forecast record.

By default, the API context includes forecast outputs, factor contributions,
regimes, aggregate historical-analog statistics, validation metrics, and
data-quality fields. Individual historical analog rows are excluded. They can be
enabled only through an explicit local setting:

```toml
EXCESS_RETURN_LLM_INCLUDE_ANALOG_ROWS = true
```

API requests use strict structured output and `store=False`. Returned language is
checked for benchmark-relative terminology, answer length, and unsupported
follow-up requests. Noncompliant drafts are retried; repeated failure produces a
disclosed deterministic evidence summary instead of showing unsafe prose.

Each accepted question and answer is appended locally under
`local_artifacts/excess_return_engine/analyst_exchanges/`. These ignored JSONL audit
files contain the forecast-run ID, question, model, evidence-scope flag, and answer,
but never the API key or raw research panels.
