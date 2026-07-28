"""Pure presentation helpers for the excess-return Streamlit app."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

import pandas as pd

from excess_return_engine.experiments import (
    SavedExperiment,
    comparison_records,
    contribution_records,
)
from excess_return_engine.features import FACTOR_REGISTRY
from excess_return_engine.model import ForecastResult

FACTOR_PRESETS = {
    "Balanced": (
        "momentum_12_1",
        "volatility_21d",
        "asset_growth",
        "leverage",
        "profit_margin",
        "roe",
        "ev_ebitda",
        "size",
    ),
    "Momentum": (
        "momentum_12_1",
        "return_1m",
        "momentum_6_1",
        "relative_volatility",
    ),
    "Fundamentals": (
        "asset_growth",
        "leverage",
        "profit_margin",
        "roe",
        "book_to_market",
        "ev_ebitda",
    ),
    "Risk & liquidity": (
        "volatility_21d",
        "relative_volatility",
        "liquidity_21d",
        "turnover",
        "size",
    ),
}

PENDING_CONFIGURATION_KEY = "_pending_saved_forecast_configuration"


def queue_saved_configuration(
    state: MutableMapping[str, Any],
    saved: SavedExperiment,
    company_label: str,
) -> None:
    matching_preset = next(
        (
            name
            for name, factors in FACTOR_PRESETS.items()
            if tuple(factors) == tuple(saved.selected_factors)
        ),
        None,
    )
    state[PENDING_CONFIGURATION_KEY] = {
        "forecast_as_of": saved.as_of_date,
        "forecast_company": company_label,
        "forecast_factors": list(saved.selected_factors),
        "forecast_interval": saved.interval_level,
        "forecast_training_window": (
            "all_available"
            if saved.training_window_months is None
            else saved.training_window_months
        ),
        "forecast_preset": matching_preset,
        "_last_forecast_preset": matching_preset,
        "applied_experiment_message": (
            f"Applied {saved.name} · run {saved.configuration_id}."
        ),
    }


def apply_pending_saved_configuration(
    state: MutableMapping[str, Any],
) -> bool:
    pending = state.pop(PENDING_CONFIGURATION_KEY, None)
    if pending is None:
        return False
    state.update(pending)
    state.pop("excess_return_result", None)
    state.pop("forecast_execution_metadata", None)
    return True


def company_options(inference: pd.DataFrame) -> list[tuple[str, int]]:
    required = {"permno", "ticker", "company"}
    missing = sorted(required - set(inference.columns))
    if missing:
        raise ValueError(f"inference panel is missing columns: {', '.join(missing)}")
    companies = (
        inference[["permno", "ticker", "company"]]
        .drop_duplicates("permno")
        .sort_values(["ticker", "company", "permno"], na_position="last")
    )
    options = []
    for row in companies.itertuples(index=False):
        ticker = str(row.ticker) if pd.notna(row.ticker) else "No ticker"
        company = str(row.company) if pd.notna(row.company) else "Unknown company"
        options.append((f"{ticker} · {company} · PERMNO {int(row.permno)}", int(row.permno)))
    return options


def factor_option_label(factor_id: str) -> str:
    definition = FACTOR_REGISTRY[factor_id]
    return f"{definition.label} · {definition.category}"


def configuration_quality(
    training: pd.DataFrame,
    inference: pd.DataFrame,
    permno: int,
    selected_factors: tuple[str, ...],
    training_window_months: int | None = None,
    minimum_required_months: int = 120,
    as_of_date: str | pd.Timestamp | None = None,
) -> dict[str, object]:
    if not selected_factors:
        return {
            "status": "blocked",
            "message": "Select at least one factor.",
            "training_rows": 0,
            "training_months": 0,
            "current_completeness": 0.0,
            "historical_coverage": 0.0,
            "correlated_pairs": (),
        }
    current = inference[inference["permno"] == permno]
    if len(current) != 1:
        return {
            "status": "blocked",
            "message": "The selected security does not have one current inference row.",
            "training_rows": 0,
            "training_months": 0,
            "current_completeness": 0.0,
            "historical_coverage": 0.0,
            "correlated_pairs": (),
        }

    relevant = training.dropna(subset=["excess_return_next_month"]).copy()
    if as_of_date is not None:
        as_of = pd.Timestamp(as_of_date).to_period("M").to_timestamp("M")
        relevant = relevant[
            pd.to_datetime(relevant["month_end"]) < as_of
        ]
    available_months = sorted(pd.to_datetime(relevant["month_end"]).unique())
    if (
        training_window_months is not None
        and training_window_months <= len(available_months)
    ):
        retained_months = set(available_months[-training_window_months:])
        relevant = relevant[
            pd.to_datetime(relevant["month_end"]).isin(retained_months)
        ]
    current_completeness = float(
        current.iloc[0][list(selected_factors)].notna().mean()
    )
    historical_coverage = float(
        relevant[list(selected_factors)].notna().mean().mean()
    )
    training_months = int(relevant["month_end"].nunique())
    correlations = relevant[list(selected_factors)].corr()
    correlated_pairs = []
    for left_index, factor_a in enumerate(selected_factors):
        for factor_b in selected_factors[left_index + 1 :]:
            correlation = correlations.loc[factor_a, factor_b]
            if pd.notna(correlation) and abs(float(correlation)) >= 0.85:
                correlated_pairs.append(
                    (factor_a, factor_b, float(correlation))
                )
    status = "ready"
    message = "Configuration passes the research minimums."
    if (
        training_window_months is not None
        and training_window_months > len(available_months)
    ):
        status = "blocked"
        message = (
            f"Only {len(available_months)} historical months are available "
            f"for the requested {training_window_months}-month window."
        )
    elif training_months < minimum_required_months:
        status = "blocked"
        message = (
            f"At least {minimum_required_months} historical months are "
            "required for fitting, tuning, and calibration."
        )
    elif current_completeness < 0.75:
        status = "blocked"
        message = "Current selected-factor completeness must be at least 75%."
    elif historical_coverage < 0.70:
        status = "blocked"
        message = "Historical selected-factor coverage must be at least 70%."

    return {
        "status": status,
        "message": message,
        "training_rows": int(len(relevant)),
        "training_months": training_months,
        "current_completeness": current_completeness,
        "historical_coverage": historical_coverage,
        "correlated_pairs": tuple(correlated_pairs),
    }


def contribution_table(result: ForecastResult) -> pd.DataFrame:
    rows = []
    for contribution in result.contributions:
        definition = FACTOR_REGISTRY[contribution.factor_id]
        rows.append(
            {
                "factor_id": contribution.factor_id,
                "factor": definition.label,
                "category": definition.category,
                "normalized_value": contribution.normalized_value,
                "coefficient": contribution.coefficient,
                "contribution": contribution.contribution,
            }
        )
    return pd.DataFrame(rows).sort_values(
        "contribution",
        key=lambda values: values.abs(),
        ascending=False,
    )


def regime_summary(result: ForecastResult, limit: int = 2) -> str:
    strongest = sorted(
        result.current_regime,
        key=lambda item: abs(item.normalized_value),
        reverse=True,
    )[:limit]
    return " · ".join(
        f"{item.regime} {FACTOR_REGISTRY[item.factor_id].label}"
        for item in strongest
    )


def regime_table(result: ForecastResult) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Factor": FACTOR_REGISTRY[item.factor_id].label,
                "Category": FACTOR_REGISTRY[item.factor_id].category,
                "Percentile": item.percentile,
                "Regime": item.regime,
            }
            for item in result.current_regime
        ]
    ).sort_values("Percentile", ascending=False)


def historical_analog_table(result: ForecastResult) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Ticker": analog.ticker or "N/A",
                "Company": analog.company or "Unknown",
                "Observation month": analog.month_end,
                "Outcome month": analog.target_month,
                "Similarity": analog.similarity,
                "Observed excess return": analog.observed_excess_return,
            }
            for analog in result.historical_evidence.analogs
        ]
    )


def reliability_component_table(result: ForecastResult) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Component": item.component,
                "Score": item.score,
                "Status": item.status,
                "Measured value": item.value,
                "Definition": item.detail,
            }
            for item in result.reliability.components
        ]
    )


def correlation_warning_table(result: ForecastResult) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Factor A": FACTOR_REGISTRY[item.factor_a].label,
                "Factor B": FACTOR_REGISTRY[item.factor_b].label,
                "Correlation": item.correlation,
            }
            for item in result.reliability.correlated_factor_pairs
        ]
    )


def calibration_table(result: ForecastResult) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Bin": item.bin_number,
                "Rows": item.rows,
                "Minimum probability": item.minimum_probability,
                "Maximum probability": item.maximum_probability,
                "Mean predicted probability": item.mean_predicted_probability,
                "Observed positive rate": item.observed_positive_rate,
            }
            for item in result.validation_diagnostics.calibration_bins
        ]
    )


def yearly_validation_table(result: ForecastResult) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Outcome year": item.outcome_year,
                "Rows": item.rows,
                "MAE": item.mae,
                "RMSE": item.rmse,
                "Directional hit rate": item.directional_hit_rate,
                "Interval coverage": item.interval_coverage,
                "Mean actual excess return": item.mean_actual_excess_return,
                "Mean predicted excess return": item.mean_predicted_excess_return,
            }
            for item in result.validation_diagnostics.yearly_metrics
        ]
    )


def challenger_diagnostics_table(result: ForecastResult) -> pd.DataFrame:
    diagnostics = result.challenger_diagnostics
    production = next(
        item
        for item in diagnostics.metrics
        if item.model_id == "elastic_net"
    )
    return pd.DataFrame(
        [
            {
                "Model": item.label,
                "Role": (
                    "Production"
                    if item.model_id == "elastic_net"
                    else "Baseline"
                    if item.model_id == "zero"
                    else "Challenger"
                ),
                "Training rows": item.training_rows,
                "Evaluation rows": item.evaluation_rows,
                "MAE": item.mae,
                "RMSE": item.rmse,
                "RMSE vs production": item.rmse - production.rmse,
                "Directional hit rate": item.directional_hit_rate,
                "OOS R² vs zero": item.oos_r2_vs_zero,
                "Best RMSE": item.model_id == diagnostics.leader_model_id,
            }
            for item in diagnostics.metrics
        ]
    ).sort_values(["RMSE", "Model"], ignore_index=True)


def experiment_comparison_table(
    experiments: tuple[SavedExperiment, ...],
) -> pd.DataFrame:
    table = pd.DataFrame(comparison_records(experiments))
    if table.empty:
        return table
    table["Factor set"] = [
        ", ".join(FACTOR_REGISTRY[factor].label for factor in item.selected_factors)
        for item in experiments
    ]
    return table


def experiment_contribution_table(
    experiments: tuple[SavedExperiment, ...],
) -> pd.DataFrame:
    table = pd.DataFrame(contribution_records(experiments))
    if table.empty:
        return table
    table["Factor"] = table["Factor ID"].map(
        lambda factor: FACTOR_REGISTRY[factor].label
    )
    return table


def predictive_strength_label(metrics: dict[str, float | int]) -> str:
    r2 = float(metrics["oos_r2_vs_zero"])
    directional = float(metrics["directional_hit_rate"])
    if r2 <= 0 or directional < 0.49:
        return "Weak"
    if r2 < 0.01 or directional < 0.52:
        return "Modest"
    if r2 < 0.03 or directional < 0.55:
        return "Moderate"
    return "Strong"
