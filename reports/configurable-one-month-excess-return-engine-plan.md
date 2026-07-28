# Configurable One-Month Excess-Return Prediction Engine

Status: Implementation started

Last reviewed: July 28, 2026

Primary users: equity research analysts, quantitative researchers, investment bankers

Primary forecast horizon: one month

Implementation status:

- Phase 1 foundation started in `excess_return_engine/data.py`.
- Local WRDS data is loaded through `WRDS_RESEARCH_DATA_DIR` and remains outside Git.
- The first build uses an explicit lagged-market-cap-weighted research benchmark.
- Labels require the exact next calendar month and no longer use the legacy row
  shift.
- Training, latest inference, and unresolved-audit panels are separate outputs.
- The existing `monthly_panel.parquet` is treated as a migration fixture because its
  legacy build dropped every security's final observed month; rebuilding from the
  enriched daily panel is implemented in `excess_return_engine/monthly.py`.
- The July 27 local validation build produced 731,107 training rows through October
  2025, 3,841 latest inference candidates, and 16,227 unresolved audit rows, with
  zero labels crossing a missing calendar month.
- The retained-final-row rebuild processed 20,052,183 daily observations into
  757,058 monthly rows for 9,724 securities through December 2025. It preserves all
  747,334 legacy monthly rows, adds exactly one final observation per security, and
  produces 740,106 calendar-safe training labels through November 2025 plus 3,935
  December 2025 inference candidates.
- A 14-factor registry and full-universe monthly rank normalization are implemented
  in `excess_return_engine/features.py`. Calendar-lagged momentum cannot cross a
  missing month, unavailable fundamentals are masked, and the old `idio_vol` proxy
  is correctly labeled `relative_volatility`.
- The first configurable Elastic Net runner is implemented in
  `excess_return_engine/model.py`. It uses chronological tuning and calibration
  windows, empirical positive-return probability and 80% prediction intervals,
  reconcilable linear contributions, versioned configuration IDs, and local
  forecast-run storage.
- A December 2025 GOOGL research run using eight selected factors completed against
  all 740,106 training rows in approximately three seconds. Its final 24-month
  holdout produced 80.5% interval coverage for the requested 80% interval and
  0.06% out-of-sample R-squared versus zero, reinforcing that outputs must display
  measured uncertainty and modest predictive strength.
- A separate local Streamlit research workflow is implemented in
  `ui/excess_return_engine/app.py`. It provides company selection by permanent
  security ID, factor presets and custom factor sets, configurable intervals,
  pre-run quality gates, headline forecast outputs, contribution attribution,
  validation and data-quality views, and reproducible JSON export.
- The research workflow was exercised end to end with a real GOOGL forecast and
  browser-verified at 1440-pixel desktop and 390-pixel mobile widths with no page
  overflow or browser errors.
- The local UI reads only ignored research artifacts and is deliberately separate
  from the public Streamlit deployment so licensed WRDS-derived data is not
  published.
- Current factor regimes and similar-condition evidence are implemented in
  `excess_return_engine/evidence.py`. Regimes are explicit percentile buckets;
  analogs are the 20 nearest historical security-months by root-mean-square
  distance in the same normalized selected-factor space used by the model.
- Forecast records now include each analog's realized next-month excess return plus
  the analog set's mean, median, positive-outcome rate, and 10th-to-90th percentile
  range. The local UI exposes the complete evidence in a dedicated tab.
- The local forecast UI now includes an evidence-grounded OpenAI analyst. It sends
  only the immutable forecast record and aggregate analog evidence by default,
  uses strict structured output with API storage disabled, pins every answer to the
  forecast-run ID, and makes suggested follow-up questions directly clickable.
- Analyst language passes deterministic benchmark-relative and evidence-availability
  checks. Failed drafts receive constrained retries, then fall back to a disclosed
  deterministic summary rather than displaying noncompliant prose.
- Questions and accepted answers are appended to ignored local JSONL audit files;
  credentials and raw WRDS research panels are never included.
- Versioned model-reliability and data-quality assessment is implemented in
  `excess_return_engine/reliability.py`. It scores out-of-sample improvement,
  probability and interval calibration, coefficient stability, current-observation
  similarity, close-analog coverage, factor completeness, history depth, and
  point-in-time status.
- Forecast records and the UI expose every score component, multivariate
  training-distance percentile, nearest similarity, correlated selected-factor
  pairs, and downgrade warnings. The real eight-factor GOOGL run scores `62.9/100`
  model reliability and `79/100` data quality; the latter is capped because
  fundamentals still use the research-lag proxy.
- Versioned holdout diagnostics are implemented in
  `excess_return_engine/validation.py`. The default 48-month calibration window
  reserves its final 24 months for untouched evaluation, producing ten equal-count
  probability-calibration bins and outcome-year validation tables for 2024 and
  2025. UI-generated runs are now saved automatically to ignored local storage.
- Versioned saved experiments are implemented in
  `excess_return_engine/experiments.py`. The local UI can name and save a compact
  forecast manifest, restore its company, selected factors, and interval, compare
  compatible runs side by side, chart contribution changes, and export the
  comparison as CSV. It surfaces explicit warnings for security, as-of, target,
  benchmark, and data-version mismatches.
- Experiment manifests remain in ignored local storage and contain configuration,
  forecast summaries, contributions, and version IDs only. They exclude raw WRDS
  rows, historical analog rows, API credentials, and licensed source files.
- Configurable trailing training windows are implemented across the model, UI,
  analyst context, configuration hash, and saved experiments. Users can compare all
  eligible history with 10-year and 12-year windows; the engine blocks windows that
  cannot preserve the required fit, tuning, and calibration splits.
- A browser-verified 10-year GOOGL run used exactly 120 months, produced run ID
  `f7b836c95eb0a7af`, and remained responsive without horizontal overflow at a
  390-pixel mobile width. Its expected excess return was `-0.3%`, with `47.3%`
  positive probability, an 80% interval of `-13.3%` to `+12.5%`, and `65/100`
  model reliability.
- Versioned challenger diagnostics are implemented in
  `excess_return_engine/challengers.py`. Zero, production Elastic Net, OLS, random
  forest, and a neural network are evaluated on the same untouched holdout. The
  challengers use only earlier rows and one deterministic 20,000-row training cap;
  they cannot alter the production forecast or attribution.
- The real 120-month GOOGL challenger run completed in 2.5 seconds over 92,017
  evaluation rows. OLS narrowly led RMSE at `16.985%`, followed by random forest at
  `16.987%` and Elastic Net at `16.991%`; the neural network underperformed the zero
  baseline. The UI discloses the leader and retains Elastic Net pending
  repeatability across windows and regimes.
- A renewed source audit confirmed that `DatasetKreunenTest` still contains
  `DlyRet` without an explicit delisting-return field and derives
  `fund_available_date` as `datadate + 3 months`; no `rdq`, filing date, or revision
  timestamp is present.
- Versioned historical as-of replay is implemented in
  `excess_return_engine/replay.py`. Eligible dates require at least 120 earlier
  months. Historical inference snapshots blank all realized stock, benchmark, and
  excess-return fields plus future benchmark aggregates before model execution.
- Replay quality checks and model fitting use only months strictly before the
  selected as-of date. The realized outcome is joined back through a separate
  post-forecast path and is labeled accordingly in the UI and LLM evidence.
- A real December 2024 GOOGL replay built a 3,856-security inference cross-section
  with every outcome field hidden. Run `5b39593247c92361` forecast `-0.61%` excess
  return for January 2025 versus a subsequently revealed `+4.41%`, a forecast error
  of `-5.03%`; this miss remains visible rather than being optimized away.
- Content-aware immutable run caching is implemented in
  `excess_return_engine/runs.py`. Configuration IDs now include a fingerprint over
  every available registered factor, rank, outcome, benchmark, security, and
  display value in the research scope plus Python, numpy, pandas, and scikit-learn
  versions.
- Versioned run artifacts persist the full request, actor, UTC creation time,
  coefficients, hyperparameters, forecast evidence, diagnostics, and source/service
  versions. Writes are atomic; stale or corrupt files are repaired, while a
  recomputation mismatch preserves the original and fails loudly. Successful
  generations, cache hits, and verification runs append actor-stamped audit events.
- On the real 120-month GOOGL configuration, run `22767630d60a2ae6` took `3.46`
  seconds to generate and `0.97` seconds to load from cache. The cached nested
  forecast record matched the generated result exactly.
- Versioned expanding-window evaluation is implemented in
  `excess_return_engine/walk_forward.py`. Each of the final 24 as-of months refits
  Elastic Net using only earlier rows; probabilities and intervals use only
  residuals available before the prediction month.
- Run `ae1ae807a81dd896` persisted 97,504 calibration residual rows and 92,017
  out-of-sample predictions in a 189,521-row ledger with an immutable logical
  content hash. Every training cutoff preceded its prediction month, and every
  target was the exact next calendar month.
- The real walk-forward evidence remains appropriately modest: `8.70%` MAE,
  `16.99%` RMSE, `48.77%` directional accuracy, `80.25%` interval coverage,
  `0.11%` out-of-sample R-squared versus zero, and `-0.025` mean monthly rank IC.
  The UI shows these results separately from the fixed-origin challenger holdout.
- Versioned selected-factor lineage and freshness assessment is implemented in
  `excess_return_engine/lineage.py`. Every model input is tied to its registered
  source columns and values, source snapshot, observation date, period end,
  availability date, availability rule, freshness classification, and
  point-in-time status.
- The pre-run gate and model runner now reject incomplete or future-dated source
  evidence. Aging and stale values remain visible and lower or cap data quality.
  Immutable run manifests, saved experiments, the Data tab, JSON output, and LLM
  context preserve the lineage version and evidence.
- Market factors use `source_last_trading_date`. Fundamentals use `datadate` and
  the existing `fund_available_date = datadate + 3 months` field, which is
  explicitly labeled `research_lag_proxy`; it is not represented as a real filing
  or announcement timestamp.
- Real 120-month GOOGL run `2a9aff6c682d57ef` traced all eight selected factors:
  freshness was `100%`, no factors were stale or aging, and five fundamental
  factors were explicitly marked as research-lag proxies. Its immutable artifact
  reloaded from cache with the same eight lineage records and
  `factor-lineage-v1` manifest version.
- Versioned forecast-scope panel audits are implemented in
  `excess_return_engine/audit.py`. Model execution blocks duplicate
  security-months, future training rows, non-contiguous target months, non-finite
  outcomes, unreconciled excess returns, benchmark mismatches, populated inference
  outcomes, missing selected-factor source dates, and future-dated source evidence.
- Audit review findings remain distinct from blockers. Extreme stock returns,
  unavailable explicit delisting fields, and fixed-lag fundamental timing are
  disclosed in immutable runs, saved experiments, the Data tab, and LLM context.
  Local panel rebuilds also write an ignored `panel_audit.json`.
- Run fingerprints now cover stock and benchmark outcome components, source dates,
  and every registered source column, so corrections beneath an unchanged derived
  value invalidate the old configuration ID.
- Real 120-month GOOGL run `91a5ed08fe70f5f9` passed all ten blocking controls
  over 495,094 historical rows and a 3,935-security inference cross-section.
  `panel-audit-v4` audit `e407472fae058c45` identified 563 stock returns above
  100% absolute return and
  retained the known delisting and fundamental-timing limitations as three review
  items. Its 13-check record includes selected-factor source-date completeness
  and content SHA-256
  `e1253e9af37a55cd49de0bb90616a437b0033cbcec01de82db697aa20a55b0b7`.
- Versioned benchmark selection is implemented in
  `excess_return_engine/benchmarks.py`. Users can choose the source
  lagged-cap-weighted covered-universe benchmark or a derived equal-weighted
  covered-universe benchmark. The selection recomputes training labels,
  validation and walk-forward outcomes, replay outcomes, run identity, saved
  experiments, UI evidence, and LLM context.
- Real 120-month GOOGL benchmark comparison produced distinct immutable runs.
  Lagged-cap-weighted run `017194d198b3442b` forecast `-0.27%` expected excess
  return with `47.29%` positive probability, while equal-weight run
  `16a18a9fb5b7ea8f` forecast `-0.42%` with `45.73%` positive probability.
  Both passed the panel audit with zero blockers. The Streamlit benchmark selector
  loaded the cached equal-weight run without errors. Fresh recomputation verified
  both immutable forecast records and their distinct walk-forward ledgers exactly.
- Delisting-return and actual fundamental-availability-date audits remain open.

## 1. Feature Summary

Extend the existing factor explorer into a configurable prediction engine. A user
selects a company, benchmark, as-of date, and a subset of available factors. The
system trains or loads a model using only those factors and produces a one-month
forward excess-return forecast.

The engine should display:

- Expected one-month excess return
- Probability of a positive excess return
- Prediction interval
- Model reliability and data-quality score
- Top positive and negative factor contributions
- Current factor regime
- Historical outcomes under similar conditions
- Historical out-of-sample model performance

The quantitative model must generate every numerical forecast. The LLM may explain
the model output, answer questions, and retrieve supporting research, but it must not
invent, modify, or independently calculate the forecast.

## 2. Product Goal

Help a user answer:

> Given the information that was actually available on this date, what one-month
> excess return does this selected factor set imply, how uncertain is that forecast,
> and what historical evidence supports it?

This feature is a decision-support and research tool. It is not intended to guarantee
future performance or replace professional judgment, independent model validation,
or the firm's risk controls.

## 3. Forecast Contract

### 3.1 Primary target

The primary model target is:

```text
one_month_excess_return =
    company_one_month_total_return
    - benchmark_one_month_total_return
```

Examples of benchmarks:

- S&P 500 ETF or index
- Nasdaq-100 ETF or index
- Sector ETF
- Industry portfolio
- User-selected peer basket

The benchmark used in training must also be used when evaluating and presenting the
forecast.

### 3.2 Absolute price presentation

The engine should forecast excess return as its primary output. An implied future
price may be displayed only after a benchmark-return assumption is supplied:

```text
expected_company_return =
    benchmark_return_assumption + expected_excess_return

implied_price =
    current_price * (1 + expected_company_return)
```

If the model uses total returns, expected dividends must be handled consistently when
converting the forecast into an ex-dividend share-price estimate. The UI should label
the result as a conditional implied price, not a guaranteed price target.

## 4. User Workflow

### Step 1: Choose the prediction scope

The user selects:

- Company
- As-of date
- One-month horizon
- Benchmark
- Training window
- Company universe used for model training

The system must prevent the user from selecting an as-of date later than the latest
fully processed data snapshot.

### Step 2: Choose factors

Reuse the current factor-selection experience and add:

- Searchable factor catalog
- Factor categories
- Saved factor sets
- Recommended presets
- Availability and freshness indicators
- Missing-data warnings
- Overlap and multicollinearity warnings
- Minimum-history requirements

Suggested presets:

- Fundamentals
- Growth and revisions
- Valuation
- Price momentum
- Quality and profitability
- Risk and volatility
- Macro sensitivity
- Balanced multi-factor

### Step 3: Validate the configuration

Before running the model, show:

- Number of selected factors
- Number of usable observations
- Date coverage
- Company coverage
- Percentage of missing values
- Point-in-time status
- Correlated or overlapping factors
- Expected model complexity
- Whether the configuration passes minimum training requirements

The system should block configurations that do not have enough valid history or that
cannot be reproduced using point-in-time data.

### Step 4: Generate the forecast

The system should:

1. Freeze the selected as-of date.
2. Load only information available at or before that time.
3. Build the selected features.
4. Load or train the appropriate model.
5. Generate the predictive distribution.
6. Calculate attribution and reliability metrics.
7. Retrieve similar historical observations.
8. Save a reproducible forecast record.

### Step 5: Review, compare, and save

Users should be able to:

- Save the configuration as an experiment
- Compare factor sets side by side
- Re-run the same configuration on another company
- Export the forecast and supporting evidence
- Share a read-only link
- Ask the LLM questions about the forecast

## 5. Output Definitions

### 5.1 Expected excess return

The mean or median of the one-month predictive distribution. The UI must state which
measure is used.

Example:

```text
Expected one-month excess return: +2.1%
Benchmark: S&P 500
As of: June 30, 2026
```

### 5.2 Probability of a positive excess return

The estimated probability that:

```text
one_month_excess_return > 0
```

This probability should come from the same predictive distribution as the expected
return and interval whenever possible. If a separate classifier is used, its
probabilities must be calibrated and checked for consistency with the return model.

### 5.3 Prediction interval

Display a prediction interval for the future outcome, not a confidence interval for
a model coefficient.

Recommended MVP presentation:

```text
80% prediction interval: -3.4% to +7.2%
```

The interface should also report historical interval coverage. An 80% interval that
contained only 50% of realized outcomes should be flagged as poorly calibrated.

### 5.4 Model reliability and data quality

Avoid presenting a vague or model-generated "confidence" score. Use a transparent
reliability score built from measurable components:

- Out-of-sample predictive performance
- Probability calibration
- Prediction-interval calibration
- Coefficient or feature-importance stability
- Training sample size
- Factor coverage and freshness
- Missing-data rate
- Similarity between the current observation and training data
- Regime coverage in the training set

Display the component scores and the overall label:

```text
Model reliability: Moderate
Data completeness: 96%
Current observation distance: Within training range
```

### 5.5 Top contributing factors

Show positive and negative model contributions in a waterfall chart.

For a linear model:

```text
factor_contribution = standardized_factor_value * fitted_coefficient
```

For a tree-based model, use a documented attribution method such as SHAP and clearly
state the baseline. Contributions explain the model forecast; they do not prove that
a factor caused a stock-price movement.

### 5.6 Current factor regime

Begin with a transparent rules-based regime model using:

- Market trend
- Realized or implied volatility
- Interest-rate direction
- Credit-spread direction
- Cross-sectional return dispersion
- Earnings-revision breadth
- Market liquidity

Example labels:

- Low volatility / positive momentum
- High volatility / defensive
- Rising rates / slowing revisions
- Recovery / improving breadth

More advanced clustering or hidden Markov models can be evaluated later.

### 5.7 Historical outcomes under similar conditions

Find prior observations using normalized selected-factor values and a documented
distance metric. Only observations earlier than the selected as-of date may be used.

Display:

| Company | Historical date | Similarity | Subsequent excess return | Regime |
|---|---:|---:|---:|---|
| Example A | 2021-04-30 | 91% | +4.2% | Positive momentum |
| Example B | 2019-08-30 | 88% | -1.1% | High volatility |

The similar-condition sample should include multiple companies when the training
universe supports it. The UI must show sample size and warn when no close historical
matches exist.

### 5.8 Historical model performance

Every forecast should include an out-of-sample performance panel:

- Mean absolute error
- Root mean squared error
- Directional hit rate
- Rank information coefficient, when applicable
- Brier score for positive-return probability
- Probability calibration chart
- Prediction-interval coverage
- Performance by market regime
- Performance by sector
- Performance by year
- Performance versus a simple baseline

Economic metrics such as simulated turnover, transaction costs, and drawdown belong
in later portfolio or signal-testing modules.

## 6. Initial Modeling Approach

### 6.1 MVP model

Start with an explainable regularized linear model:

- Elastic Net regression for expected excess return
- Standardized numeric inputs
- Time-aware preprocessing
- Walk-forward training and validation
- Empirical or conformal residual distribution
- Regime-aware residuals when enough observations exist

This approach supports:

- On-demand selected-factor models
- Clear factor contributions
- Regularization of correlated factors
- Reproducible coefficients
- Faster training and caching

### 6.2 Comparison models

Evaluate later models against the MVP baseline:

- Ordinary least squares
- Ridge and Lasso regression
- Gradient-boosted trees
- Random forest
- Quantile regression
- Panel regression with company and sector controls
- Bayesian regression
- Regime-specific models

An advanced model should not replace the baseline unless it produces a repeatable
out-of-sample improvement after costs and remains sufficiently interpretable for its
intended use.

### 6.3 Training design

Use walk-forward evaluation:

```text
train through time t
predict t + one month
record the prediction and outcome
advance to the next as-of date
repeat
```

Do not use random train/test splits for the primary financial validation.

When labels overlap because of the one-month horizon, use appropriate embargo or
purging around validation boundaries. Fit imputers, scalers, feature selectors, and
all model parameters using training data only.

### 6.4 Dynamic factor subsets

Each unique configuration should be identified by:

```text
company universe
benchmark
selected factors
training window
as-of date
data version
feature version
model version
```

Use this configuration hash as the cache and experiment identifier. A forecast must
be regenerated whenever any component changes.

For the MVP, models can be trained on demand and cached. Precompute popular presets
later if training latency becomes disruptive.

## 7. Factor Catalog

The catalog should eventually support:

### Fundamentals

- Revenue growth
- EPS growth
- Free-cash-flow growth
- EBITDA growth
- Margin level and change
- Return on invested capital
- Accruals
- Net debt and leverage
- Share-count change

### Valuation

- Price-to-earnings
- Enterprise-value-to-EBITDA
- Enterprise-value-to-sales
- Free-cash-flow yield
- Earnings yield
- Book-to-market
- Relative valuation versus sector

### Growth and analyst revisions

- Revenue-estimate revisions
- EPS-estimate revisions
- Estimate dispersion
- Estimate breadth
- Earnings surprise
- Guidance change
- Target-price revisions

### Momentum and technical

- One-, three-, six-, and twelve-month momentum
- Short-term reversal
- Distance from moving averages
- Relative strength versus benchmark
- Volume trend
- Gap and post-earnings drift measures

### Risk and liquidity

- Realized volatility
- Downside volatility
- Beta
- Idiosyncratic volatility
- Maximum drawdown
- Average dollar volume
- Bid-ask spread
- Short interest
- Options-implied volatility

### Macro and regime

- Treasury yields
- Yield-curve slope
- Inflation
- Policy rate
- Credit spreads
- Dollar index
- Commodity prices
- Market volatility
- Economic-surprise measures

## 8. Point-in-Time Data Requirements

The largest implementation risk is not model selection. It is accidentally training
on information that was revised, restated, or published after the prediction date.

Each observation should preserve:

- `company_id`
- `security_id`
- `ticker_as_of_date`
- `observation_date`
- `period_end_date`
- `published_at`
- `available_at`
- `source`
- `source_record_id`
- `revision_id`
- `value`
- `currency`
- `units`
- `ingested_at`
- `data_version`

For filings, store both the fiscal period and filing acceptance timestamp. For analyst
estimates, store every historical snapshot or revision rather than only the latest
consensus. For macroeconomic data, use vintage values when revisions are material.

The security master should handle:

- Ticker changes
- Multiple share classes
- Mergers and acquisitions
- Spin-offs
- Delistings
- IPO dates
- Exchange changes
- Splits and dividends
- Permanent company and security identifiers

## 9. Data Sources

### 9.1 Existing WRDS research asset: DatasetKreunenTest

#### Decision

Use the local `DatasetKreunenTest` project as the starting research and engineering
foundation for this feature. It already solves several expensive parts of the
problem: CRSP-Compustat identifier linking, inclusion of inactive securities,
daily-to-monthly aggregation, factor construction, cross-sectional preprocessing,
walk-forward model evaluation, and storage of out-of-sample predictions.

Do not use its current target, predictions, or performance claims directly in the
user-facing engine. The project is a strong prototype, not yet a production-quality
point-in-time excess-return system. The target and several data controls must be
corrected first.

#### Measured inventory

The following profile was measured from the local files on July 23, 2026:

| Asset | Rows or coverage | Intended use in the engine |
|---|---:|---|
| `CRSPTest.csv` | Approximately 30 million daily rows | Daily price, total-return, and volume history |
| `CompustatTest.csv` | Annual accounting observations | Fundamental factors |
| `CCMTest.csv` | Dated CRSP-Compustat links | Map `gvkey` to permanent CRSP identifiers |
| `CompanyNamesTest.csv` | Dated issuer names and trading symbols | Time-aware display names and ticker history |
| `final_quant_dataset.parquet` | 20,065,382 rows | Existing linked daily research panel |
| `final_with_signals.parquet` | 20,052,183 rows | Existing daily factors |
| `final_with_ev.parquet` | 20,052,183 rows | Existing enriched daily input to the monthly pipeline |
| `monthly_panel.parquet` | 747,334 rows, 9,537 securities, 179 months | Starting point for corrected monthly labels |
| `predictions.parquet` | 243,224 rows, 6,556 securities, January 2021-November 2025 | Baseline comparison and regression testing only |

The monthly panel covers January 2011 through November 2025 and has a median of
approximately 4,218 securities per month. The data therefore has enough
cross-sectional breadth and history for an initial U.S. equity panel model.

The existing factor set contains:

- Momentum: 12-1 momentum, one-month reversal, and 6-1 momentum
- Risk: 21-day realized volatility and a volatility-relative-to-market proxy
- Liquidity: 21-day liquidity and turnover
- Fundamentals: asset growth, leverage, profit margin, and return on equity
- Valuation: enterprise-value-to-EBITDA and book-to-market
- Size: log market capitalization

Observed non-null coverage ranges from approximately 70.2% for
enterprise-value-to-EBITDA to 100% for size. Missingness must be exposed in the
forecast's data-quality score rather than hidden by preprocessing.

#### Components to reuse

Reuse or adapt these parts of `DatasetKreunenTest`:

- The dated `PERMNO`/`gvkey`/ticker linking approach
- CRSP daily-return compounding into monthly total returns
- Existing factor definitions where they pass the audits below
- Monthly cross-sectional rank normalization to `[-1, 1]`
- Expanding-window annual validation as an initial backtest framework
- OLS, random-forest, and neural-network outputs as comparison baselines
- Existing decile, feature-ablation, and out-of-sample evaluation code
- Parquet artifacts as reproducible pipeline checkpoints

The existing OLS, random forest, and neural network should be retained as benchmark
models. Add Elastic Net as the first configurable production baseline because it is
fast to retrain for arbitrary factor subsets and produces directly reconcilable
factor contributions.

#### Mandatory corrections before modeling

1. **Create the correct excess-return target.** The current `y_next` is the next
   observed raw stock return. Add a monthly benchmark total-return table and define:

   ```text
   y_excess_next =
       stock_total_return_for_calendar_month_t_plus_1
       - benchmark_total_return_for_calendar_month_t_plus_1
   ```

   Store both component returns, the benchmark identifier, and the final excess
   return. The same benchmark and return convention must be used for training,
   evaluation, and display.

2. **Require exact calendar-month continuity.** The current pipeline uses a
   per-security row shift. Profiling found 6,690 adjacent security rows where the
   next observation is more than one calendar month later. Those rows must not be
   labeled as one-month-forward outcomes. Generate a label only when the next
   observation is exactly month `t + 1`, or join explicitly on
   `(PERMNO, calendar_month + 1)`.

3. **Keep the latest unlabeled inference row.** The current monthly build drops rows
   without a future realized return. Create separate training and inference views so
   the latest factor observation remains available for a live forecast.

4. **Audit return extremes and delistings.** The measured `y_next` distribution has
   a maximum of approximately 6,691%. The source extract contains `DlyRet` but no
   explicit delisting-return field. Reconcile extreme observations against CRSP,
   document whether `DlyRet` already incorporates delisting outcomes, and combine
   regular and delisting returns correctly when required. Any winsorization must be
   fit on training data and documented; do not silently alter realized test outcomes.

5. **Strengthen point-in-time fundamentals.** The current project assumes that an
   annual Compustat observation becomes available three months after `datadate`.
   The extract does not include `rdq`, filing dates, or revision timestamps. Use the
   fixed lag only for an explicitly labeled research prototype. For a validated
   engine, obtain actual announcement or filing availability dates and preserve
   historical versions.

6. **Correct factor semantics.** The existing `idio_vol` is calculated as stock
   volatility minus the monthly cross-sectional average. Rename it as a relative
   volatility proxy or replace it with residual volatility from a documented market
   or factor model.

7. **Validate accounting units and tails.** Book-to-market, turnover, leverage,
   profitability, and enterprise-value ratios require unit checks, denominator
   guards, industry-specific treatment, and cross-sectional outlier tests.

8. **Parameterize the selected factors.** The model functions can accept an input
   matrix, but the driver currently hardcodes all 14 features. Pass the user's
   selected factor identifiers through feature validation, preprocessing, training,
   attribution, storage, and cache-key construction.

9. **Fit preprocessing inside each training window.** Preserve the current
   cross-sectional rank concept, but ensure all clipping, imputation, scaling, and
   feature-selection parameters are learned without validation or test information.
   Store missingness indicators and per-factor freshness.

10. **Persist complete model runs.** In addition to row-level predictions, save the
    fitted model, selected factor list, coefficients or feature importance, training
    dates, benchmark, universe, preprocessing state, package versions, data version,
    and configuration hash.

#### Missing inputs to obtain

The local extracts do not contain every field required by this plan. Add:

- A benchmark total-return series for each supported benchmark
- Explicit delisting returns or written confirmation of their treatment
- Filing or announcement availability timestamps for fundamentals
- Sector and industry history, preferably point-in-time SIC, GICS, or equivalent
- Current incremental CRSP and Compustat updates after November 2025
- Analyst-estimate history from LSEG I/B/E/S if revisions become selectable factors
- Macro vintages from ALFRED if macro factors or regimes use revised economic data

These are additions to the current foundation, not reasons to discard it.

#### Integration architecture

Keep the licensed WRDS pipeline separate from the public application repository:

```text
WRDS extracts
  -> private immutable raw storage
  -> corrected point-in-time daily panel
  -> monthly feature and benchmark tables
  -> training view with realized excess-return labels
  -> latest inference view without future labels
  -> model registry and forecast-run store
  -> permissioned API
  -> Streamlit forecast UI and read-only LLM tools
```

Use stable IDs internally (`PERMNO`, `PERMCO`, and `gvkey`) and resolve tickers only
for display. A forecast request should never identify a security solely by its
current ticker.

Suggested migration from the existing project:

1. Copy reusable transformations into testable modules in the application project;
   do not make the 12 GB research directory a runtime dependency.
2. Build a small, versioned, non-licensed fixture that reproduces important edge
   cases for automated tests.
3. Implement calendar-safe monthly stock and benchmark labels.
4. Create separate `training_panel` and `inference_panel` outputs.
5. Add a factor registry containing definition, source columns, availability rule,
   coverage, units, and version.
6. Add an Elastic Net runner that accepts a validated factor subset.
7. Store walk-forward predictions and calibration residuals by configuration hash.
8. Add probability, conformal interval, attribution, regime, neighbor, and
   reliability services on top of the saved model run.
9. Expose only those services to the LLM; never send the full licensed panel to the
   model.

#### Licensing and deployment boundary

CRSP, Compustat, and other WRDS-hosted datasets are licensed products. Do not commit
raw extracts or row-level derived datasets to GitHub, package them into a public
Streamlit deployment, or send them to an external LLM until the applicable
entitlements explicitly permit those uses.

The existing data project's `.gitignore` already excludes CSV and Parquet files.
Maintain that control and add secret scanning, artifact checks, and deployment
allowlists. A public demonstration should use synthetic, separately licensed, or
sufficiently aggregated data. The firm-facing version should use private storage,
authentication, entitlement checks, and a private deployment.

#### Dataset-specific acceptance gates

Before `DatasetKreunenTest` can power an internal engine release:

- Zero one-month labels may cross a missing calendar month.
- Stock and benchmark total-return conventions must reconcile on sampled periods.
- Extreme returns and delisting cases must pass a documented manual audit.
- Every fundamental value must have an availability timestamp and source lineage.
- The latest inference panel must contain no future return or benchmark outcome.
- Every selectable factor must pass unit, coverage, freshness, and point-in-time
  tests.
- The configured model must prove it used exactly the selected factors.
- Walk-forward metrics must be recomputed for excess returns, including calibration
  and interval coverage.
- Forecast outputs must carry security, benchmark, data, feature, and model versions.
- No licensed dataset or API secret may be present in Git history or public build
  artifacts.

Provider offerings, pricing, and licenses change. Confirm current commercial,
redistribution, and derived-data rights before using any source in a firm-facing
product.

### 9.2 Free and official sources

| Source | Best use | Strengths | Important limitations |
|---|---|---|---|
| [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | Filings, XBRL fundamentals, filing timestamps | Free, official, real-time submissions and nightly bulk files | Requires normalization, taxonomy mapping, restatement handling, and careful filing-date logic |
| [FRED and ALFRED APIs](https://fred.stlouisfed.org/docs/api/fred/) | Rates, inflation, employment, credit and macro series | Large catalog; ALFRED supports historical vintages | Release timing and vintage selection must be handled explicitly |
| [Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) | Academic factor returns and portfolio benchmarks | Widely used factor datasets | Better for benchmarking than security-level production data |
| [U.S. Treasury Fiscal Data APIs](https://fiscaldata.treasury.gov/api-documentation/) | Treasury and fiscal series | Official and free | Not a replacement for complete market-rate data |
| [Cboe historical market data](https://www.cboe.com/us/indices/market_statistics/historical_data/) | VIX and selected index history | Official source for important volatility indices | Detailed options datasets may require commercial licensing |

The SEC APIs do not require API keys. They provide submissions history and extracted
XBRL facts, but raw XBRL facts still require accounting and point-in-time validation.

### 9.3 Lower-cost prototyping APIs

| Provider | Potential use | Notes |
|---|---|---|
| [Alpha Vantage](https://www.alphavantage.co/documentation/) | Prices, statements, earnings, estimates, news and technical indicators | Useful for prototypes; verify historical depth, rate limits, point-in-time behavior, and commercial rights |
| [Tiingo](https://www.tiingo.com/documentation/end-of-day) | Adjusted prices, corporate actions, fundamentals and news | Provides stable identifiers for some delisted or recycled tickers; fundamental coverage is an add-on |
| [Massive](https://massive.com/docs/rest/stocks/overview) | Market prices, ticker reference data, corporate actions and selected fundamentals | Formerly Polygon.io; check plan-specific history and business-use licenses |
| [Financial Modeling Prep](https://site.financialmodelingprep.com/developer/docs) | Statements, prices, estimates, segments and calendars | Convenient API surface; independently verify point-in-time and revision semantics |
| [Nasdaq Data Link](https://docs.data.nasdaq.com/) | Vendor datasets through a common API | Dataset quality, coverage, and cost vary by publisher |

These sources can accelerate an MVP, but a successful API response does not prove
that the data is suitable for historical forecasting. Specifically ask whether the
provider includes:

- Inactive and delisted securities
- Point-in-time fundamentals
- Historical estimate snapshots
- Original publication timestamps
- Restatements and revisions
- Split and dividend adjustments
- Commercial display and redistribution rights

`yfinance` is acceptable for a local demonstration or a rough cross-check. It should
not be the sole production source for a firm-facing forecasting system because it is
not a contracted institutional data feed and may not provide the required lineage,
service guarantees, or redistribution rights.

### 9.4 Institutional and research-grade sources

| Provider | Potential use | Why it matters |
|---|---|---|
| [WRDS](https://wrds-www.wharton.upenn.edu/) | Access platform for CRSP, Compustat, LSEG I/B/E/S, OptionMetrics, TAQ and other datasets | Particularly useful when a university or firm already has subscriptions and needs historical identifier links |
| [CRSP](https://www.crsp.org/) | Research-grade security prices, returns, distributions and delisting history | Strong foundation for survivorship-aware U.S. equity research |
| [S&P Compustat / Capital IQ](https://www.spglobal.com/market-intelligence/en/solutions/products/fundamental-data) | Point-in-time fundamentals, estimates, company and sector data | Strong historical normalization, estimate snapshots, coverage and auditability |
| [Visible Alpha](https://www.spglobal.com/market-intelligence/en/solutions/visible-alpha-on-sp-capital-iq-pro) | Detailed sell-side operating-model estimates | Useful for segment and operating-driver research |
| [FactSet](https://developer.factset.com/) | Prices, returns, fundamentals, estimates, ownership and point-in-time data | Broad institutional workflow and API coverage |
| [LSEG Data & Analytics](https://developers.lseg.com/) | Market data, fundamentals, news, Datastream and I/B/E/S estimates | Useful for global data and historical analyst expectations |
| [Bloomberg Enterprise Data](https://professional.bloomberg.com/products/data/enterprise-catalog/) | Market, reference, fundamental, estimate and derived data | Common firm infrastructure; licensing and delivery are enterprise-oriented |

For a serious one-month forecasting engine, historical analyst-estimate revisions are
often difficult to source correctly. If the firm already licenses Bloomberg, FactSet,
S&P Capital IQ, LSEG, or WRDS, investigate that entitlement before buying a separate
API.

### 9.5 Recommended source combinations

#### Lowest-cost research prototype

- Prices and corporate actions: Tiingo or another contracted lower-cost provider
- Fundamentals: SEC EDGAR XBRL
- Macro: FRED and ALFRED
- Benchmark factors: Kenneth French Data Library
- Estimates: Alpha Vantage or Financial Modeling Prep for initial experimentation

This combination still requires substantial cleaning and may not provide complete
historical estimate snapshots.

#### Academic or university research

- Prices and delistings: CRSP through WRDS
- Fundamentals: Compustat through WRDS
- Estimates and revisions: LSEG I/B/E/S through WRDS
- Macro: FRED and ALFRED
- Options: OptionMetrics through WRDS, when available

#### Firm-grade deployment

Prefer the firm's existing enterprise vendor and entitlements:

- FactSet
- S&P Capital IQ / Compustat / Visible Alpha
- LSEG
- Bloomberg

Use SEC EDGAR and FRED as independent validation or supplemental sources. Avoid
mixing vendors without a documented identifier, currency, timestamp, and revision
reconciliation process.

## 10. Data-Source Evaluation Checklist

Before adopting a provider, document:

- Security and company coverage
- Active and inactive security coverage
- Earliest reliable history
- Point-in-time availability
- Revision and restatement history
- Timestamp precision and time zone
- Corporate-action methodology
- Stable identifiers
- Currency treatment
- Survivorship-bias controls
- API rate limits
- Bulk-download support
- Service-level agreement
- Historical correction policy
- Commercial use rights
- Display rights
- Derived-data rights
- Redistribution rights
- LLM and machine-learning usage rights
- Data retention requirements
- Total expected annual cost

Run a vendor bake-off using the same 20-50 companies and manually reconcile a sample
against original filings and known corporate actions before committing to a source.

## 11. LLM Responsibilities

The LLM may:

- Explain the forecast in plain language
- Answer questions about selected factors
- Compare saved configurations
- Retrieve internal research and model documentation
- Cite the exact model run and source data
- Explain model limitations
- Suggest follow-up analyses

The LLM must not:

- Generate the numerical forecast
- Change the selected factors without user confirmation
- Present attribution as causation
- Hide failed validation checks
- Invent unavailable financial values
- Provide unsupported certainty
- override risk, entitlement, or model-governance controls

Each LLM answer about a forecast should include the immutable forecast-run ID so the
underlying numbers remain traceable.

## 12. Reproducibility and Governance

Persist a record for every forecast:

- Forecast-run ID
- User and timestamp
- Company and security identifiers
- As-of date
- Benchmark
- Selected factors
- Raw source snapshot IDs
- Feature values
- Preprocessing version
- Training dates
- Model type and hyperparameters
- Model artifact version
- Expected return
- Predictive distribution
- Reliability components
- Similar historical observations
- Validation results
- LLM explanation and retrieved citations

Do not silently replace old forecasts after source corrections or model updates.
Create a new version and preserve the original result.

## 13. Failure States and Guardrails

Block or downgrade the forecast when:

- Required source data is unavailable
- The latest factor is stale
- Too few observations remain after filtering
- The current observation is materially outside the training distribution
- Selected factors are nearly duplicates
- The walk-forward model materially underperforms the baseline
- Prediction intervals are poorly calibrated
- The selected company lacks sufficient history
- The model has not been validated for the selected sector or regime

Example message:

```text
Forecast unavailable

This configuration has only 38 usable historical observations and two selected
factors contain information that was not available point-in-time. Adjust the training
window or remove the affected factors.
```

## 14. Phased Delivery

### Phase 1: Data and target foundation

- Migrate reusable `DatasetKreunenTest` transformations into tested modules
- Select the default benchmark and define total-return conventions
- Enforce exact calendar-month continuity in labels
- Create benchmark-relative one-month excess-return labels
- Separate historical training rows from current unlabeled inference rows
- Audit extreme returns, delistings, corporate actions, and accounting units
- Replace the fixed fundamental lag with actual availability dates, or explicitly
  limit the first release to research-prototype status
- Add data-quality and licensed-artifact leakage tests

### Phase 2: Explainable model baseline

- Add Elastic Net forecasting
- Refactor the model runner to accept an explicit selected-factor list
- Recompute walk-forward validation against the excess-return target
- Add empirical or conformal intervals
- Add reproducible model-run storage
- Compare against the existing OLS, random-forest, and neural-network baselines

### Phase 3: Configurable factor UX

- Reuse and extend the factor picker
- Add presets and saved configurations
- Add overlap and coverage warnings
- Add run caching
- Add side-by-side experiment comparison

### Phase 4: Forecast evidence

- Add contribution waterfall
- Add probability and calibration views
- Add regime labels
- Add historical nearest neighbors
- Add reliability components

### Phase 5: LLM analyst

- Give the LLM read-only access to forecast tools
- Add firm-document retrieval
- Require source and forecast-run citations
- Build an evaluation set from real analyst questions

### Phase 6: Firm readiness

- SSO and role-based access
- Data entitlements
- Audit logs
- Model inventory
- Independent validation workflow
- Monitoring and alerting
- Private deployment and cost controls

## 15. MVP Acceptance Criteria

The initial feature is ready for internal testing when:

- A user can select a company, benchmark, as-of date, and factor subset.
- Every factor value is traceable to a source and availability timestamp.
- The model uses only the selected factors.
- The model is trained without future information.
- Walk-forward predictions are stored and reproducible.
- Expected excess return, positive probability, and interval are internally
  consistent.
- The interval includes an observed historical coverage statistic.
- Factor contributions reconcile to the model prediction within a documented
  tolerance.
- Similar-condition examples occur before the selected as-of date.
- The UI blocks configurations below minimum data standards.
- Every forecast includes model and data versions.
- The LLM can explain but cannot modify the quantitative result.

## 16. Open Decisions

- Which company and sector universe should be first?
- Which benchmark should be the default?
- Should the target use price return or total return?
- What minimum history is required per selected factor?
- Should the first model be company-specific or a multi-company panel?
- Which reliability components and thresholds should be shown?
- Which prediction interval level should be the default?
- Which market-regime definition should be used initially?
- Which vendor licenses are already available through the firm or school?
- Can derived data and LLM-generated explanations be displayed to other users under
  those licenses?

## 17. Recommended Next Decision

The existing WRDS dataset resolves the initial data-foundation decision, but not the
forecast contract. Before implementing the prediction UI, lock down these four
items:

1. Initial U.S. company universe and minimum liquidity/price filters
2. Default benchmark and total-return convention
3. Whether the first release may use the three-month fundamental lag as a clearly
   labeled research prototype or must wait for actual availability timestamps
4. Elastic Net training and monthly versus annual refit schedule

Then correct the label pipeline and rerun the walk-forward study before treating any
existing model result as evidence. The UI and LLM explanation layer should be built
on top of that validated contract.
