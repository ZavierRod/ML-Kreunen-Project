"""Leakage-safe challenger-model diagnostics for a forecast holdout."""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

CHALLENGER_VERSION = "challenger-suite-v1"
DEFAULT_MAXIMUM_TRAINING_ROWS = 20_000


@dataclass(frozen=True)
class ChallengerMetric:
    model_id: str
    label: str
    training_rows: int
    evaluation_rows: int
    mae: float
    rmse: float
    directional_hit_rate: float
    oos_r2_vs_zero: float


@dataclass(frozen=True)
class ChallengerDiagnostics:
    version: str
    maximum_training_rows: int
    sampled_training_rows: int
    evaluation_rows: int
    leader_model_id: str
    metrics: tuple[ChallengerMetric, ...]


def evaluate_challengers(
    training: pd.DataFrame,
    validation: pd.DataFrame,
    selected_factors: tuple[str, ...],
    target_column: str,
    production_predictions: np.ndarray,
    *,
    maximum_training_rows: int = DEFAULT_MAXIMUM_TRAINING_ROWS,
    random_state: int = 0,
) -> ChallengerDiagnostics:
    """Compare production and challenger regressors on one untouched holdout."""
    if maximum_training_rows < 1:
        raise ValueError("maximum_training_rows must be positive")
    if training.empty or validation.empty:
        raise ValueError("training and validation frames must not be empty")
    if len(production_predictions) != len(validation):
        raise ValueError("production predictions must match validation rows")

    required = {target_column, *selected_factors}
    missing_training = sorted(required - set(training.columns))
    missing_validation = sorted(required - set(validation.columns))
    if missing_training or missing_validation:
        missing = sorted(set(missing_training + missing_validation))
        raise ValueError(f"challenger frames are missing columns: {', '.join(missing)}")

    sampled = (
        training.sample(
            n=maximum_training_rows,
            random_state=random_state,
        )
        if len(training) > maximum_training_rows
        else training
    )
    x_train = sampled[list(selected_factors)].to_numpy(dtype=float)
    raw_y_train = sampled[target_column].to_numpy(dtype=float)
    clip_lower, clip_upper = np.quantile(raw_y_train, (0.001, 0.999))
    y_train = np.clip(raw_y_train, clip_lower, clip_upper)
    x_validation = validation[list(selected_factors)].to_numpy(dtype=float)
    y_validation = validation[target_column].to_numpy(dtype=float)

    LinearRegression, RandomForestRegressor, MLPRegressor = _load_models()
    model_specs = (
        (
            "ols",
            "Ordinary least squares",
            LinearRegression(),
        ),
        (
            "random_forest",
            "Random forest",
            RandomForestRegressor(
                n_estimators=40,
                max_depth=10,
                min_samples_leaf=20,
                max_features="sqrt",
                n_jobs=-1,
                random_state=random_state,
            ),
        ),
        (
            "neural_network",
            "Neural network",
            MLPRegressor(
                hidden_layer_sizes=(16,),
                activation="relu",
                solver="adam",
                batch_size=512,
                learning_rate_init=0.001,
                max_iter=80,
                early_stopping=True,
                validation_fraction=0.15,
                n_iter_no_change=8,
                random_state=random_state,
            ),
        ),
    )

    metrics = [
        _metric(
            model_id="zero",
            label="Zero excess-return baseline",
            predictions=np.zeros(len(validation), dtype=float),
            actual=y_validation,
            training_rows=0,
        ),
        _metric(
            model_id="elastic_net",
            label="Production Elastic Net",
            predictions=np.asarray(production_predictions, dtype=float),
            actual=y_validation,
            training_rows=len(training),
        ),
    ]
    for model_id, label, model in model_specs:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(x_train, y_train)
        predictions = model.predict(x_validation)
        metrics.append(
            _metric(
                model_id=model_id,
                label=label,
                predictions=np.asarray(predictions, dtype=float),
                actual=y_validation,
                training_rows=len(sampled),
            )
        )

    leader = min(metrics, key=lambda item: item.rmse)
    return ChallengerDiagnostics(
        version=CHALLENGER_VERSION,
        maximum_training_rows=maximum_training_rows,
        sampled_training_rows=len(sampled),
        evaluation_rows=len(validation),
        leader_model_id=leader.model_id,
        metrics=tuple(metrics),
    )


def _metric(
    *,
    model_id: str,
    label: str,
    predictions: np.ndarray,
    actual: np.ndarray,
    training_rows: int,
) -> ChallengerMetric:
    residual = actual - predictions
    baseline_error = float(np.sum(np.square(actual)))
    model_error = float(np.sum(np.square(residual)))
    oos_r2 = (
        float("nan")
        if baseline_error == 0
        else float(1 - model_error / baseline_error)
    )
    return ChallengerMetric(
        model_id=model_id,
        label=label,
        training_rows=int(training_rows),
        evaluation_rows=len(actual),
        mae=float(np.mean(np.abs(residual))),
        rmse=float(np.sqrt(np.mean(np.square(residual)))),
        directional_hit_rate=float(
            np.mean((actual > 0) == (predictions > 0))
        ),
        oos_r2_vs_zero=oos_r2,
    )


def _load_models():
    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.linear_model import LinearRegression
        from sklearn.neural_network import MLPRegressor
    except ImportError as exc:  # pragma: no cover - environment-specific.
        raise RuntimeError(
            "scikit-learn is required for challenger diagnostics. "
            "Install requirements.txt."
        ) from exc
    return LinearRegression, RandomForestRegressor, MLPRegressor
