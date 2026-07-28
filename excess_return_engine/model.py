"""Configurable Elastic Net forecast with time-aware calibration and attribution."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .features import (
    FEATURE_VERSION,
    rank_normalize_factors,
    ranked_factor_column,
    validate_factor_selection,
)
from .evidence import (
    FactorRegime,
    HistoricalEvidence,
    classify_factor_regimes,
    find_similar_conditions,
)

MODEL_VERSION = "elastic-net-panel-v1"
TARGET_VERSION = "calendar-excess-return-v1"
TARGET_COLUMN = "excess_return_next_month"
MONTH_COLUMN = "month_end"
SECURITY_COLUMN = "permno"


@dataclass(frozen=True)
class ForecastRequest:
    permno: int
    selected_factors: tuple[str, ...]
    as_of_date: str | None = None
    interval_level: float = 0.80
    tuning_months: int = 12
    calibration_months: int = 24
    minimum_training_months: int = 60
    maximum_tuning_rows: int = 150_000
    similar_observations: int = 20
    target_clip_quantiles: tuple[float, float] = (0.001, 0.999)
    alpha_grid: tuple[float, ...] = (0.00001, 0.0001, 0.001)
    l1_ratio_grid: tuple[float, ...] = (0.1, 0.5, 0.9)

    def __post_init__(self) -> None:
        validate_factor_selection(self.selected_factors)
        if not 0 < self.interval_level < 1:
            raise ValueError("interval_level must be between 0 and 1")
        if self.tuning_months < 1 or self.calibration_months < 4:
            raise ValueError("tuning_months must be positive and calibration_months >= 4")
        if self.maximum_tuning_rows < 1:
            raise ValueError("maximum_tuning_rows must be positive")
        if self.similar_observations < 1:
            raise ValueError("similar_observations must be positive")
        lower, upper = self.target_clip_quantiles
        if not 0 <= lower < upper <= 1:
            raise ValueError("target_clip_quantiles must be ordered within [0, 1]")
        if not self.alpha_grid or any(alpha <= 0 for alpha in self.alpha_grid):
            raise ValueError("alpha_grid values must be positive")
        if not self.l1_ratio_grid or any(
            not 0 <= ratio <= 1 for ratio in self.l1_ratio_grid
        ):
            raise ValueError("l1_ratio_grid values must be within [0, 1]")


@dataclass(frozen=True)
class FactorContribution:
    factor_id: str
    normalized_value: float
    coefficient: float
    contribution: float


@dataclass(frozen=True)
class ForecastResult:
    configuration_id: str
    model_version: str
    feature_version: str
    target_version: str
    data_version: str
    permno: int
    ticker: str | None
    company: str | None
    as_of_date: str
    target_month: str
    benchmark_id: str
    selected_factors: tuple[str, ...]
    expected_excess_return: float
    probability_positive: float
    interval_level: float
    interval_lower: float
    interval_upper: float
    intercept: float
    contributions: tuple[FactorContribution, ...]
    current_regime: tuple[FactorRegime, ...]
    historical_evidence: HistoricalEvidence
    model_parameters: dict[str, float]
    validation_metrics: dict[str, float | int]
    data_quality: dict[str, float | int | str]
    target_clip_bounds: tuple[float, float]

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["selected_factors"] = list(self.selected_factors)
        result["contributions"] = [
            asdict(contribution) for contribution in self.contributions
        ]
        result["current_regime"] = [
            asdict(regime) for regime in self.current_regime
        ]
        result["historical_evidence"] = asdict(self.historical_evidence)
        return result


def _load_elastic_net():
    try:
        from sklearn.linear_model import ElasticNet
    except ImportError as exc:  # pragma: no cover - environment-specific.
        raise RuntimeError(
            "scikit-learn is required for forecasting. Install requirements.txt."
        ) from exc
    return ElasticNet


def _month_end(value: object) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    return timestamp.to_period("M").to_timestamp("M")


def _validate_model_panels(
    training_panel: pd.DataFrame,
    inference_panel: pd.DataFrame,
    selected_factors: tuple[str, ...],
) -> None:
    training_required = {
        SECURITY_COLUMN,
        MONTH_COLUMN,
        TARGET_COLUMN,
        "benchmark_id",
        *selected_factors,
    }
    inference_required = {
        SECURITY_COLUMN,
        MONTH_COLUMN,
        "target_month",
        "benchmark_id",
        *selected_factors,
    }
    missing_training = sorted(training_required - set(training_panel.columns))
    missing_inference = sorted(inference_required - set(inference_panel.columns))
    if missing_training:
        raise ValueError(
            f"training panel is missing columns: {', '.join(missing_training)}"
        )
    if missing_inference:
        raise ValueError(
            f"inference panel is missing columns: {', '.join(missing_inference)}"
        )


def _clip_target(
    target: np.ndarray,
    quantiles: tuple[float, float],
) -> tuple[np.ndarray, tuple[float, float]]:
    lower, upper = np.quantile(target, quantiles)
    return np.clip(target, lower, upper), (float(lower), float(upper))


def _fit_model(
    x: np.ndarray,
    y: np.ndarray,
    alpha: float,
    l1_ratio: float,
):
    ElasticNet = _load_elastic_net()
    model = ElasticNet(
        alpha=alpha,
        l1_ratio=l1_ratio,
        fit_intercept=True,
        max_iter=10_000,
        selection="cyclic",
    )
    model.fit(x, y)
    return model


def _mean_squared_error(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.square(actual - predicted)))


def _select_parameters(
    fit_frame: pd.DataFrame,
    tuning_frame: pd.DataFrame,
    selected_factors: tuple[str, ...],
    request: ForecastRequest,
) -> tuple[dict[str, float], tuple[float, float]]:
    tuning_fit = (
        fit_frame.sample(
            n=request.maximum_tuning_rows,
            random_state=0,
        )
        if len(fit_frame) > request.maximum_tuning_rows
        else fit_frame
    )
    x_fit = tuning_fit[list(selected_factors)].to_numpy(dtype=float)
    y_fit_raw = tuning_fit[TARGET_COLUMN].to_numpy(dtype=float)
    y_fit, clip_bounds = _clip_target(
        y_fit_raw,
        request.target_clip_quantiles,
    )
    x_tuning = tuning_frame[list(selected_factors)].to_numpy(dtype=float)
    y_tuning = tuning_frame[TARGET_COLUMN].to_numpy(dtype=float)

    best: dict[str, float] | None = None
    for alpha in request.alpha_grid:
        for l1_ratio in request.l1_ratio_grid:
            model = _fit_model(x_fit, y_fit, alpha, l1_ratio)
            prediction = model.predict(x_tuning)
            mse = _mean_squared_error(y_tuning, prediction)
            candidate = {
                "alpha": float(alpha),
                "l1_ratio": float(l1_ratio),
                "tuning_mse": mse,
                "tuning_fit_rows": float(len(tuning_fit)),
            }
            if best is None or candidate["tuning_mse"] < best["tuning_mse"]:
                best = candidate
    assert best is not None
    return best, clip_bounds


def _normalized_model_frames(
    historical: pd.DataFrame,
    inference_cross_section: pd.DataFrame,
    selected_factors: tuple[str, ...],
    permno: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rank_columns = [ranked_factor_column(factor) for factor in selected_factors]
    if set(rank_columns).issubset(historical.columns) and set(rank_columns).issubset(
        inference_cross_section.columns
    ):
        ranked_historical = historical.copy()
        ranked_inference = inference_cross_section.copy()
        for factor, rank_column in zip(selected_factors, rank_columns):
            ranked_historical[factor] = ranked_historical[rank_column]
            ranked_inference[factor] = ranked_inference[rank_column]
    else:
        combined = pd.concat(
            [
                historical.assign(_panel_role="training"),
                inference_cross_section.assign(_panel_role="inference"),
            ],
            ignore_index=True,
            sort=False,
        )
        ranked = rank_normalize_factors(combined, selected_factors)
        ranked_historical = ranked[ranked["_panel_role"] == "training"].copy()
        ranked_inference = ranked[ranked["_panel_role"] == "inference"].copy()

    ranked_current = ranked_inference[
        ranked_inference[SECURITY_COLUMN] == permno
    ]
    return ranked_historical, ranked_current


def _empirical_probability_positive(
    prediction: np.ndarray,
    residuals: np.ndarray,
) -> np.ndarray:
    sorted_residuals = np.sort(residuals)
    first_strictly_greater = np.searchsorted(
        sorted_residuals,
        -prediction,
        side="right",
    )
    return (len(sorted_residuals) - first_strictly_greater) / len(
        sorted_residuals
    )


def _validation_metrics(
    validation: pd.DataFrame,
    predictions: np.ndarray,
    calibration_residuals: np.ndarray,
    residual_bounds: tuple[float, float],
) -> dict[str, float | int]:
    actual = validation[TARGET_COLUMN].to_numpy(dtype=float)
    residual = actual - predictions
    probability = _empirical_probability_positive(
        predictions,
        calibration_residuals,
    )
    lower_residual, upper_residual = residual_bounds
    covered = (actual >= predictions + lower_residual) & (
        actual <= predictions + upper_residual
    )
    baseline_error = float(np.sum(np.square(actual)))
    model_error = float(np.sum(np.square(residual)))
    oos_r2 = float("nan") if baseline_error == 0 else 1 - model_error / baseline_error
    return {
        "evaluation_rows": int(len(validation)),
        "evaluation_months": int(validation[MONTH_COLUMN].nunique()),
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(np.square(residual)))),
        "directional_hit_rate": float(np.mean((actual > 0) == (predictions > 0))),
        "brier_score": float(np.mean(np.square((actual > 0).astype(float) - probability))),
        "interval_coverage": float(np.mean(covered)),
        "oos_r2_vs_zero": oos_r2,
    }


def _configuration_id(
    request: ForecastRequest,
    as_of: pd.Timestamp,
    benchmark_id: str,
    data_version: str,
) -> str:
    payload = {
        "permno": request.permno,
        "selected_factors": list(request.selected_factors),
        "as_of_date": as_of.date().isoformat(),
        "benchmark_id": benchmark_id,
        "data_version": data_version,
        "interval_level": request.interval_level,
        "tuning_months": request.tuning_months,
        "calibration_months": request.calibration_months,
        "minimum_training_months": request.minimum_training_months,
        "maximum_tuning_rows": request.maximum_tuning_rows,
        "similar_observations": request.similar_observations,
        "target_clip_quantiles": list(request.target_clip_quantiles),
        "alpha_grid": list(request.alpha_grid),
        "l1_ratio_grid": list(request.l1_ratio_grid),
        "feature_version": FEATURE_VERSION,
        "model_version": MODEL_VERSION,
        "target_version": TARGET_VERSION,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def generate_forecast(
    training_panel: pd.DataFrame,
    inference_panel: pd.DataFrame,
    request: ForecastRequest,
) -> ForecastResult:
    """Fit the selected-factor model and forecast one security's next month."""
    selected = validate_factor_selection(request.selected_factors)
    _validate_model_panels(training_panel, inference_panel, selected)

    training = training_panel.copy()
    inference = inference_panel.copy()
    training[MONTH_COLUMN] = pd.to_datetime(training[MONTH_COLUMN])
    inference[MONTH_COLUMN] = pd.to_datetime(inference[MONTH_COLUMN])
    inference["target_month"] = pd.to_datetime(inference["target_month"])
    as_of = (
        _month_end(request.as_of_date)
        if request.as_of_date is not None
        else inference[MONTH_COLUMN].max()
    )

    current = inference[
        (inference[SECURITY_COLUMN] == request.permno)
        & (inference[MONTH_COLUMN] == as_of)
    ]
    if len(current) != 1:
        raise ValueError(
            f"Expected one inference row for permno={request.permno} "
            f"at {as_of.date()}, found {len(current)}."
        )
    current = current.iloc[0]
    historical = training[training[MONTH_COLUMN] < as_of].copy()
    historical = historical.dropna(subset=[TARGET_COLUMN])
    if historical.empty:
        raise ValueError("No historical labels are available before the as-of date.")

    ranked_historical, ranked_current = _normalized_model_frames(
        historical,
        inference[inference[MONTH_COLUMN] == as_of],
        selected,
        request.permno,
    )
    if len(ranked_current) != 1:
        raise ValueError("The normalized inference cross-section is not unique.")

    months = np.array(sorted(ranked_historical[MONTH_COLUMN].unique()))
    required_months = (
        request.minimum_training_months
        + request.tuning_months
        + request.calibration_months
    )
    if len(months) < required_months:
        raise ValueError(
            f"Configuration requires at least {required_months} historical months; "
            f"found {len(months)}."
        )
    calibration_start = len(months) - request.calibration_months
    tuning_start = calibration_start - request.tuning_months
    fit_months = set(months[:tuning_start])
    tuning_months = set(months[tuning_start:calibration_start])
    calibration_months = months[calibration_start:]

    fit_frame = ranked_historical[
        ranked_historical[MONTH_COLUMN].isin(fit_months)
    ]
    tuning_frame = ranked_historical[
        ranked_historical[MONTH_COLUMN].isin(tuning_months)
    ]
    calibration_frame = ranked_historical[
        ranked_historical[MONTH_COLUMN].isin(set(calibration_months))
    ]
    best, _ = _select_parameters(
        fit_frame,
        tuning_frame,
        selected,
        request,
    )

    pre_calibration = ranked_historical[
        ranked_historical[MONTH_COLUMN] < pd.Timestamp(calibration_months[0])
    ]
    y_pre_raw = pre_calibration[TARGET_COLUMN].to_numpy(dtype=float)
    y_pre, _ = _clip_target(y_pre_raw, request.target_clip_quantiles)
    calibration_model = _fit_model(
        pre_calibration[list(selected)].to_numpy(dtype=float),
        y_pre,
        best["alpha"],
        best["l1_ratio"],
    )
    calibration_predictions = calibration_model.predict(
        calibration_frame[list(selected)].to_numpy(dtype=float)
    )
    calibration_frame = calibration_frame.copy()
    calibration_frame["_prediction"] = calibration_predictions
    split_index = max(1, request.calibration_months // 2)
    residual_fit_months = set(calibration_months[:split_index])
    residual_eval_months = set(calibration_months[split_index:])
    residual_fit = calibration_frame[
        calibration_frame[MONTH_COLUMN].isin(residual_fit_months)
    ]
    residual_eval = calibration_frame[
        calibration_frame[MONTH_COLUMN].isin(residual_eval_months)
    ]
    calibration_residuals = (
        residual_fit[TARGET_COLUMN] - residual_fit["_prediction"]
    ).to_numpy(dtype=float)
    if calibration_residuals.size == 0 or residual_eval.empty:
        raise ValueError("Calibration window did not produce enough residual observations.")

    tail_probability = (1 - request.interval_level) / 2
    residual_bounds = (
        float(np.quantile(calibration_residuals, tail_probability)),
        float(np.quantile(calibration_residuals, 1 - tail_probability)),
    )
    metrics = _validation_metrics(
        residual_eval,
        residual_eval["_prediction"].to_numpy(dtype=float),
        calibration_residuals,
        residual_bounds,
    )

    y_all_raw = ranked_historical[TARGET_COLUMN].to_numpy(dtype=float)
    y_all, final_clip_bounds = _clip_target(
        y_all_raw,
        request.target_clip_quantiles,
    )
    final_model = _fit_model(
        ranked_historical[list(selected)].to_numpy(dtype=float),
        y_all,
        best["alpha"],
        best["l1_ratio"],
    )
    x_current = ranked_current[list(selected)].to_numpy(dtype=float)
    point_forecast = float(final_model.predict(x_current)[0])
    probability_positive = float(
        _empirical_probability_positive(
            np.array([point_forecast]),
            calibration_residuals,
        )[0]
    )
    normalized_values = x_current[0]
    current_regime = classify_factor_regimes(selected, normalized_values)
    historical_evidence = find_similar_conditions(
        ranked_historical,
        selected,
        normalized_values,
        request.similar_observations,
        TARGET_COLUMN,
    )
    contributions = tuple(
        FactorContribution(
            factor_id=factor_id,
            normalized_value=float(value),
            coefficient=float(coefficient),
            contribution=float(value * coefficient),
        )
        for factor_id, value, coefficient in zip(
            selected,
            normalized_values,
            final_model.coef_,
        )
    )
    reconciled = float(final_model.intercept_) + sum(
        contribution.contribution for contribution in contributions
    )
    if not np.isclose(reconciled, point_forecast, atol=1e-10):
        raise RuntimeError("Factor contributions do not reconcile to the forecast.")

    benchmark_ids = historical["benchmark_id"].dropna().astype(str).unique()
    current_benchmark = str(current["benchmark_id"])
    if len(benchmark_ids) != 1 or benchmark_ids[0] != current_benchmark:
        raise ValueError("Training and inference panels must use one matching benchmark.")
    raw_current = inference[
        (inference[SECURITY_COLUMN] == request.permno)
        & (inference[MONTH_COLUMN] == as_of)
    ].iloc[0]
    selected_completeness = float(
        raw_current[list(selected)].notna().mean()
    )
    training_coverage = float(
        historical[list(selected)].notna().mean().mean()
    )
    training_start = historical[MONTH_COLUMN].min().date().isoformat()
    training_end = historical[MONTH_COLUMN].max().date().isoformat()
    data_version = (
        f"rows-{len(historical)}_months-{training_start}-to-{training_end}"
    )

    return ForecastResult(
        configuration_id=_configuration_id(
            request,
            as_of,
            current_benchmark,
            data_version,
        ),
        model_version=MODEL_VERSION,
        feature_version=FEATURE_VERSION,
        target_version=TARGET_VERSION,
        data_version=data_version,
        permno=int(request.permno),
        ticker=_optional_string(current.get("ticker")),
        company=_optional_string(current.get("company")),
        as_of_date=as_of.date().isoformat(),
        target_month=pd.Timestamp(current["target_month"]).date().isoformat(),
        benchmark_id=current_benchmark,
        selected_factors=selected,
        expected_excess_return=point_forecast,
        probability_positive=probability_positive,
        interval_level=request.interval_level,
        interval_lower=point_forecast + residual_bounds[0],
        interval_upper=point_forecast + residual_bounds[1],
        intercept=float(final_model.intercept_),
        contributions=contributions,
        current_regime=current_regime,
        historical_evidence=historical_evidence,
        model_parameters=best,
        validation_metrics=metrics,
        data_quality={
            "selected_factor_completeness": selected_completeness,
            "historical_factor_coverage": training_coverage,
            "training_rows": int(len(ranked_historical)),
            "training_months": int(ranked_historical[MONTH_COLUMN].nunique()),
            "calibration_residual_rows": int(len(calibration_residuals)),
            "point_in_time_status": "research_lag_proxy",
        },
        target_clip_bounds=final_clip_bounds,
    )


def _optional_string(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(value)


def save_forecast_result(
    result: ForecastResult,
    output_dir: str | Path,
) -> Path:
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    output_path = destination / f"{result.configuration_id}.json"
    output_path.write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a configurable one-month excess-return research forecast."
    )
    parser.add_argument("--permno", type=int, required=True)
    parser.add_argument("--factors", nargs="+", required=True)
    parser.add_argument(
        "--training-panel",
        default="local_artifacts/excess_return_engine/training_panel.parquet",
    )
    parser.add_argument(
        "--inference-panel",
        default="local_artifacts/excess_return_engine/inference_panel.parquet",
    )
    parser.add_argument(
        "--output-dir",
        default="local_artifacts/excess_return_engine/forecast_runs",
    )
    parser.add_argument("--as-of-date")
    parser.add_argument("--interval-level", type=float, default=0.80)
    args = parser.parse_args()

    training = pd.read_parquet(Path(args.training_panel).expanduser().resolve())
    inference = pd.read_parquet(Path(args.inference_panel).expanduser().resolve())
    request = ForecastRequest(
        permno=args.permno,
        selected_factors=tuple(args.factors),
        as_of_date=args.as_of_date,
        interval_level=args.interval_level,
    )
    result = generate_forecast(training, inference, request)
    output_path = save_forecast_result(result, args.output_dir)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    print(f"saved: {output_path}")


if __name__ == "__main__":
    main()
