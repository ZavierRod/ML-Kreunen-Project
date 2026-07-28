"""Auditable holdout diagnostics for forecast probability and return outputs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

VALIDATION_VERSION = "holdout-diagnostics-v1"


@dataclass(frozen=True)
class CalibrationBin:
    bin_number: int
    rows: int
    minimum_probability: float
    maximum_probability: float
    mean_predicted_probability: float
    observed_positive_rate: float


@dataclass(frozen=True)
class YearlyValidation:
    outcome_year: int
    rows: int
    mae: float
    rmse: float
    directional_hit_rate: float
    interval_coverage: float
    mean_actual_excess_return: float
    mean_predicted_excess_return: float


@dataclass(frozen=True)
class ValidationDiagnostics:
    calibration_bins: tuple[CalibrationBin, ...]
    yearly_metrics: tuple[YearlyValidation, ...]


def build_validation_diagnostics(
    *,
    validation: pd.DataFrame,
    predictions: np.ndarray,
    probabilities: np.ndarray,
    residual_bounds: tuple[float, float],
    target_column: str,
    month_column: str,
    bin_count: int = 10,
) -> ValidationDiagnostics:
    if bin_count < 2:
        raise ValueError("bin_count must be at least 2")
    actual = validation[target_column].to_numpy(dtype=float)
    predicted = np.asarray(predictions, dtype=float)
    probability = np.asarray(probabilities, dtype=float)
    if len(actual) != len(predicted) or len(actual) != len(probability):
        raise ValueError("validation arrays must have matching lengths")
    if len(actual) == 0:
        raise ValueError("validation diagnostics require at least one row")

    order = np.argsort(probability, kind="stable")
    calibration_bins = []
    for bin_number, indices in enumerate(
        np.array_split(order, min(bin_count, len(order))),
        start=1,
    ):
        if len(indices) == 0:
            continue
        bin_probability = probability[indices]
        bin_actual = actual[indices]
        calibration_bins.append(
            CalibrationBin(
                bin_number=bin_number,
                rows=int(len(indices)),
                minimum_probability=float(np.min(bin_probability)),
                maximum_probability=float(np.max(bin_probability)),
                mean_predicted_probability=float(np.mean(bin_probability)),
                observed_positive_rate=float(np.mean(bin_actual > 0)),
            )
        )

    outcome_month = (
        pd.to_datetime(validation["target_month"])
        if "target_month" in validation.columns
        else pd.to_datetime(validation[month_column]) + pd.offsets.MonthEnd(1)
    )
    diagnostic_frame = pd.DataFrame(
        {
            "outcome_year": outcome_month.dt.year.to_numpy(),
            "actual": actual,
            "predicted": predicted,
        }
    )
    lower_residual, upper_residual = residual_bounds
    diagnostic_frame["covered"] = (
        (diagnostic_frame["actual"] >= diagnostic_frame["predicted"] + lower_residual)
        & (
            diagnostic_frame["actual"]
            <= diagnostic_frame["predicted"] + upper_residual
        )
    )
    diagnostic_frame["direction_correct"] = (
        (diagnostic_frame["actual"] > 0)
        == (diagnostic_frame["predicted"] > 0)
    )
    diagnostic_frame["absolute_error"] = (
        diagnostic_frame["actual"] - diagnostic_frame["predicted"]
    ).abs()
    diagnostic_frame["squared_error"] = np.square(
        diagnostic_frame["actual"] - diagnostic_frame["predicted"]
    )

    yearly_metrics = []
    for year, group in diagnostic_frame.groupby("outcome_year", sort=True):
        yearly_metrics.append(
            YearlyValidation(
                outcome_year=int(year),
                rows=int(len(group)),
                mae=float(group["absolute_error"].mean()),
                rmse=float(np.sqrt(group["squared_error"].mean())),
                directional_hit_rate=float(group["direction_correct"].mean()),
                interval_coverage=float(group["covered"].mean()),
                mean_actual_excess_return=float(group["actual"].mean()),
                mean_predicted_excess_return=float(group["predicted"].mean()),
            )
        )

    return ValidationDiagnostics(
        calibration_bins=tuple(calibration_bins),
        yearly_metrics=tuple(yearly_metrics),
    )
