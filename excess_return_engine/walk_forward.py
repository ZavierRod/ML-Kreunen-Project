"""Expanding-window monthly evaluation with point-in-time residual calibration."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

WALK_FORWARD_VERSION = "expanding-walk-forward-v1"


@dataclass(frozen=True)
class WalkForwardMonth:
    as_of_date: str
    target_month: str
    training_rows: int
    evaluation_rows: int
    mae: float
    rmse: float
    directional_hit_rate: float
    brier_score: float
    interval_coverage: float
    rank_ic: float | None
    mean_actual_excess_return: float
    mean_predicted_excess_return: float


@dataclass(frozen=True)
class WalkForwardDiagnostics:
    version: str
    evaluation_start: str
    evaluation_end: str
    evaluation_months: int
    evaluation_rows: int
    calibration_residual_rows: int
    mae: float
    rmse: float
    directional_hit_rate: float
    brier_score: float
    interval_coverage: float
    oos_r2_vs_zero: float
    mean_rank_ic: float | None
    monthly_metrics: tuple[WalkForwardMonth, ...]


@dataclass(frozen=True)
class WalkForwardEvaluation:
    diagnostics: WalkForwardDiagnostics
    predictions: pd.DataFrame


def evaluate_walk_forward(
    *,
    historical: pd.DataFrame,
    calibration_residual_frame: pd.DataFrame,
    selected_factors: tuple[str, ...],
    target_column: str,
    month_column: str,
    alpha: float,
    l1_ratio: float,
    interval_level: float,
    target_clip_quantiles: tuple[float, float],
    evaluation_month_count: int,
) -> WalkForwardEvaluation:
    """Refit monthly and predict each cross-section using only earlier outcomes."""
    if evaluation_month_count < 1:
        raise ValueError("evaluation_month_count must be positive")
    required = {
        "permno",
        month_column,
        target_column,
        *selected_factors,
    }
    missing = sorted(required - set(historical.columns))
    if missing:
        raise ValueError(
            f"walk-forward panel is missing columns: {', '.join(missing)}"
        )
    calibration_required = {
        "permno",
        month_column,
        target_column,
        "_prediction",
    }
    missing_calibration = sorted(
        calibration_required - set(calibration_residual_frame.columns)
    )
    if missing_calibration:
        raise ValueError(
            "calibration residual frame is missing columns: "
            + ", ".join(missing_calibration)
        )

    panel = historical.copy()
    panel[month_column] = pd.to_datetime(panel[month_column])
    months = np.array(sorted(panel[month_column].unique()))
    if len(months) <= evaluation_month_count:
        raise ValueError("Not enough months for walk-forward evaluation.")
    evaluation_months = months[-evaluation_month_count:]

    calibration = calibration_residual_frame.copy()
    calibration[month_column] = pd.to_datetime(calibration[month_column])
    if calibration[month_column].max() >= pd.Timestamp(
        evaluation_months[0]
    ):
        raise ValueError(
            "Calibration residuals must precede every evaluation month."
        )
    calibration_residuals = (
        calibration[target_column] - calibration["_prediction"]
    ).to_numpy(dtype=float)
    if calibration_residuals.size == 0 or not np.isfinite(
        calibration_residuals
    ).all():
        raise ValueError("Walk-forward evaluation requires calibration residuals.")
    calibration_start = calibration[month_column].min()
    calibration_training = panel[
        panel[month_column] < calibration_start
    ]
    if calibration_training.empty:
        raise ValueError(
            "Calibration residuals have no earlier training rows."
        )
    residual_history = calibration_residuals.copy()
    records = [
        _calibration_records(
            calibration,
            target_column,
            month_column,
            training_end=calibration_training[month_column].max(),
            training_rows=len(calibration_training),
        )
    ]
    monthly_metrics = []

    for evaluation_month in evaluation_months:
        training = panel[panel[month_column] < evaluation_month]
        evaluation = panel[panel[month_column] == evaluation_month]
        if training.empty or evaluation.empty:
            raise ValueError("Walk-forward month has no training or evaluation rows.")
        y_training_raw = training[target_column].to_numpy(dtype=float)
        clip_lower, clip_upper = np.quantile(
            y_training_raw,
            target_clip_quantiles,
        )
        y_training = np.clip(
            y_training_raw,
            clip_lower,
            clip_upper,
        )
        model = _fit_model(
            training[list(selected_factors)].to_numpy(dtype=float),
            y_training,
            alpha,
            l1_ratio,
        )
        predicted = model.predict(
            evaluation[list(selected_factors)].to_numpy(dtype=float)
        )
        actual = evaluation[target_column].to_numpy(dtype=float)
        probability = _probability_positive(predicted, residual_history)
        tail = (1 - interval_level) / 2
        lower_residual = float(np.quantile(residual_history, tail))
        upper_residual = float(np.quantile(residual_history, 1 - tail))
        lower = predicted + lower_residual
        upper = predicted + upper_residual
        residual = actual - predicted
        target_month = _target_month(evaluation, evaluation_month, month_column)
        rank_ic = _rank_ic(actual, predicted)

        monthly_metrics.append(
            WalkForwardMonth(
                as_of_date=pd.Timestamp(evaluation_month).date().isoformat(),
                target_month=target_month.date().isoformat(),
                training_rows=int(len(training)),
                evaluation_rows=int(len(evaluation)),
                mae=float(np.mean(np.abs(residual))),
                rmse=float(np.sqrt(np.mean(np.square(residual)))),
                directional_hit_rate=float(
                    np.mean((actual > 0) == (predicted > 0))
                ),
                brier_score=float(
                    np.mean(
                        np.square((actual > 0).astype(float) - probability)
                    )
                ),
                interval_coverage=float(
                    np.mean((actual >= lower) & (actual <= upper))
                ),
                rank_ic=rank_ic,
                mean_actual_excess_return=float(np.mean(actual)),
                mean_predicted_excess_return=float(np.mean(predicted)),
            )
        )
        records.append(
            pd.DataFrame(
                {
                    "permno": evaluation["permno"].to_numpy(dtype=np.int64),
                    "as_of_date": pd.Timestamp(evaluation_month),
                    "target_month": target_month,
                    "actual_excess_return": actual,
                    "predicted_excess_return": predicted,
                    "residual": residual,
                    "probability_positive": probability,
                    "interval_lower": lower,
                    "interval_upper": upper,
                    "interval_level": interval_level,
                    "split": "walk_forward_evaluation",
                    "training_end": pd.Timestamp(
                        training[month_column].max()
                    ),
                    "training_rows": int(len(training)),
                }
            )
        )
        residual_history = np.concatenate([residual_history, residual])

    predictions = pd.concat(records, ignore_index=True)
    evaluation_predictions = predictions[
        predictions["split"] == "walk_forward_evaluation"
    ]
    actual = evaluation_predictions["actual_excess_return"].to_numpy(
        dtype=float
    )
    predicted = evaluation_predictions["predicted_excess_return"].to_numpy(
        dtype=float
    )
    residual = actual - predicted
    baseline_error = float(np.sum(np.square(actual)))
    model_error = float(np.sum(np.square(residual)))
    finite_rank_ic = [
        item.rank_ic
        for item in monthly_metrics
        if item.rank_ic is not None and np.isfinite(item.rank_ic)
    ]
    return WalkForwardEvaluation(
        diagnostics=WalkForwardDiagnostics(
            version=WALK_FORWARD_VERSION,
            evaluation_start=pd.Timestamp(
                evaluation_months[0]
            ).date().isoformat(),
            evaluation_end=pd.Timestamp(
                evaluation_months[-1]
            ).date().isoformat(),
            evaluation_months=len(evaluation_months),
            evaluation_rows=int(len(evaluation_predictions)),
            calibration_residual_rows=int(len(calibration)),
            mae=float(np.mean(np.abs(residual))),
            rmse=float(np.sqrt(np.mean(np.square(residual)))),
            directional_hit_rate=float(
                np.mean((actual > 0) == (predicted > 0))
            ),
            brier_score=float(
                np.mean(
                    np.square(
                        (actual > 0).astype(float)
                        - evaluation_predictions[
                            "probability_positive"
                        ].to_numpy(dtype=float)
                    )
                )
            ),
            interval_coverage=float(
                np.mean(
                    (
                        actual
                        >= evaluation_predictions["interval_lower"].to_numpy(
                            dtype=float
                        )
                    )
                    & (
                        actual
                        <= evaluation_predictions["interval_upper"].to_numpy(
                            dtype=float
                        )
                    )
                )
            ),
            oos_r2_vs_zero=(
                float("nan")
                if baseline_error == 0
                else float(1 - model_error / baseline_error)
            ),
            mean_rank_ic=(
                None
                if not finite_rank_ic
                else float(np.mean(finite_rank_ic))
            ),
            monthly_metrics=tuple(monthly_metrics),
        ),
        predictions=predictions,
    )


def _fit_model(
    x: np.ndarray,
    y: np.ndarray,
    alpha: float,
    l1_ratio: float,
):
    try:
        from sklearn.linear_model import ElasticNet
    except ImportError as exc:  # pragma: no cover - environment-specific.
        raise RuntimeError(
            "scikit-learn is required for walk-forward evaluation."
        ) from exc
    model = ElasticNet(
        alpha=alpha,
        l1_ratio=l1_ratio,
        fit_intercept=True,
        max_iter=10_000,
        selection="cyclic",
    )
    model.fit(x, y)
    return model


def _probability_positive(
    prediction: np.ndarray,
    residuals: np.ndarray,
) -> np.ndarray:
    sorted_residuals = np.sort(residuals)
    boundary = np.searchsorted(
        sorted_residuals,
        -prediction,
        side="right",
    )
    return (len(sorted_residuals) - boundary) / len(sorted_residuals)


def _target_month(
    evaluation: pd.DataFrame,
    evaluation_month: object,
    month_column: str,
) -> pd.Timestamp:
    if "target_month" not in evaluation:
        return pd.Timestamp(evaluation_month) + pd.offsets.MonthEnd(1)
    target_months = pd.to_datetime(evaluation["target_month"]).unique()
    if len(target_months) != 1:
        raise ValueError("Walk-forward month has multiple target months.")
    expected = pd.Timestamp(evaluation_month) + pd.offsets.MonthEnd(1)
    target_month = pd.Timestamp(target_months[0])
    if target_month != expected:
        raise ValueError(
            f"{month_column} does not map to the exact next target month."
        )
    return target_month


def _rank_ic(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    actual_rank = pd.Series(actual).rank(method="average")
    predicted_rank = pd.Series(predicted).rank(method="average")
    correlation = actual_rank.corr(predicted_rank)
    if pd.isna(correlation):
        return None
    return float(correlation)


def _calibration_records(
    calibration: pd.DataFrame,
    target_column: str,
    month_column: str,
    *,
    training_end: object,
    training_rows: int,
) -> pd.DataFrame:
    predicted = calibration["_prediction"].to_numpy(dtype=float)
    actual = calibration[target_column].to_numpy(dtype=float)
    as_of = pd.to_datetime(calibration[month_column])
    target_month = (
        pd.to_datetime(calibration["target_month"])
        if "target_month" in calibration
        else as_of + pd.offsets.MonthEnd(1)
    )
    if not (target_month == as_of + pd.offsets.MonthEnd(1)).all():
        raise ValueError(
            "Calibration residual target is not the exact next month."
        )
    return pd.DataFrame(
        {
            "permno": calibration["permno"].to_numpy(dtype=np.int64),
            "as_of_date": as_of,
            "target_month": target_month,
            "actual_excess_return": actual,
            "predicted_excess_return": predicted,
            "residual": actual - predicted,
            "probability_positive": np.nan,
            "interval_lower": np.nan,
            "interval_upper": np.nan,
            "interval_level": np.nan,
            "split": "calibration_residual",
            "training_end": pd.Timestamp(training_end),
            "training_rows": int(training_rows),
        }
    )
