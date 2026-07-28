"""Transparent model-reliability and data-quality assessment."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

RELIABILITY_VERSION = "reliability-v2"


@dataclass(frozen=True)
class ReliabilityComponent:
    component: str
    score: float
    status: str
    value: str
    detail: str


@dataclass(frozen=True)
class FactorCorrelation:
    factor_a: str
    factor_b: str
    correlation: float


@dataclass(frozen=True)
class ReliabilityAssessment:
    model_reliability_score: float
    model_reliability_label: str
    data_quality_score: float
    data_quality_label: str
    current_distance_percentile: float
    current_distance_status: str
    nearest_similarity: float
    close_analog_count: int
    components: tuple[ReliabilityComponent, ...]
    correlated_factor_pairs: tuple[FactorCorrelation, ...]
    warnings: tuple[str, ...]


def assess_reliability(
    *,
    historical: pd.DataFrame,
    selected_factors: tuple[str, ...],
    normalized_values: np.ndarray,
    validation_metrics: dict[str, float | int],
    interval_level: float,
    calibration_coefficients: np.ndarray,
    final_coefficients: np.ndarray,
    selected_factor_completeness: float,
    historical_factor_coverage: float,
    training_months: int,
    point_in_time_status: str,
    analog_similarities: tuple[float, ...],
    factor_freshness_score: float = 1.0,
    factor_lineage_status: str = "Verified",
    correlation_threshold: float = 0.85,
) -> ReliabilityAssessment:
    """Score only observable reliability inputs and retain their warnings."""
    matrix = historical[list(selected_factors)].to_numpy(dtype=np.float32)
    current = np.asarray(normalized_values, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[1] != len(current):
        raise ValueError("historical factors and normalized_values do not align")
    if matrix.shape[0] == 0:
        raise ValueError("historical factors are empty")

    center = np.median(matrix, axis=0)
    historical_radius = np.sqrt(np.mean(np.square(matrix - center), axis=1))
    current_radius = float(np.sqrt(np.mean(np.square(current - center))))
    distance_percentile = float(np.mean(historical_radius <= current_radius))
    distance_score = float(np.clip((1.0 - distance_percentile) / 0.10, 0.0, 1.0))
    if distance_percentile <= 0.90:
        distance_status = "Within typical training range"
    elif distance_percentile <= 0.97:
        distance_status = "Near training-range edge"
    else:
        distance_status = "Outside typical training range"

    nearest_similarity = max(analog_similarities, default=0.0)
    close_analog_count = sum(value >= 0.90 for value in analog_similarities)
    similarity_score = float(np.clip((nearest_similarity - 0.75) / 0.20, 0.0, 1.0))
    regime_coverage_score = float(np.clip(close_analog_count / 10.0, 0.0, 1.0))

    oos_r2 = float(validation_metrics["oos_r2_vs_zero"])
    predictive_score = float(np.clip((oos_r2 + 0.005) / 0.035, 0.0, 1.0))
    brier_score = float(validation_metrics["brier_score"])
    brier_baseline = float(validation_metrics["brier_baseline"])
    brier_skill = (
        0.0
        if brier_baseline <= 0
        else float(1.0 - brier_score / brier_baseline)
    )
    probability_score = float(np.clip((brier_skill + 0.05) / 0.20, 0.0, 1.0))
    interval_coverage = float(validation_metrics["interval_coverage"])
    interval_error = abs(interval_coverage - interval_level)
    interval_score = float(np.clip(1.0 - interval_error / 0.20, 0.0, 1.0))
    coefficient_score = _coefficient_stability(
        calibration_coefficients,
        final_coefficients,
    )

    model_score = 100.0 * (
        0.25 * predictive_score
        + 0.15 * probability_score
        + 0.20 * interval_score
        + 0.15 * coefficient_score
        + 0.15 * similarity_score
        + 0.10 * regime_coverage_score
    )

    history_score = float(np.clip((training_months - 60) / 60.0, 0.0, 1.0))
    point_in_time_score = 1.0 if point_in_time_status == "verified" else 0.5
    freshness_score = float(np.clip(factor_freshness_score, 0.0, 1.0))
    data_score = 100.0 * (
        0.35 * selected_factor_completeness
        + 0.25 * historical_factor_coverage
        + 0.15 * point_in_time_score
        + 0.10 * history_score
        + 0.15 * freshness_score
    )
    if point_in_time_status != "verified":
        data_score = min(data_score, 79.0)
    if factor_lineage_status == "Stale":
        data_score = min(data_score, 59.0)
    elif factor_lineage_status == "Incomplete":
        data_score = min(data_score, 39.0)

    correlations = _correlated_factor_pairs(
        historical,
        selected_factors,
        correlation_threshold,
    )
    warnings = []
    if oos_r2 <= 0:
        warnings.append(
            "The holdout model did not outperform the zero-excess-return baseline."
        )
    if brier_skill <= 0:
        warnings.append(
            "Positive-return probabilities did not beat the calibration-window "
            "constant-probability baseline."
        )
    if interval_error > 0.10:
        warnings.append(
            "Realized prediction-interval coverage differs from its requested level "
            "by more than 10 percentage points."
        )
    if distance_percentile > 0.97:
        warnings.append(
            "The current selected-factor vector is outside the typical training range."
        )
    if close_analog_count < 5:
        warnings.append(
            "Fewer than five historical analogs have at least 90% similarity."
        )
    if correlations:
        warnings.append(
            "Selected factors include highly correlated pairs; individual "
            "contributions may be unstable."
        )
    if point_in_time_status != "verified":
        warnings.append(
            "Fundamental point-in-time availability uses the research-lag proxy."
        )
    if factor_lineage_status == "Aging":
        warnings.append(
            "At least one selected factor is based on aging source evidence."
        )
    elif factor_lineage_status == "Stale":
        warnings.append(
            "At least one selected factor is based on stale source evidence."
        )
    elif factor_lineage_status == "Incomplete":
        warnings.append(
            "At least one selected factor has incomplete source lineage."
        )

    components = (
        _component(
            "Out-of-sample improvement",
            predictive_score,
            f"{oos_r2:+.2%} R² vs zero",
            "Holdout squared-error improvement over a zero excess-return forecast.",
        ),
        _component(
            "Probability calibration",
            probability_score,
            f"{brier_skill:+.2%} Brier skill",
            "Brier-score improvement over the calibration-window base rate.",
        ),
        _component(
            "Prediction-interval calibration",
            interval_score,
            f"{interval_coverage:.1%} realized vs {interval_level:.1%} requested",
            "Closeness of realized holdout coverage to the requested interval.",
        ),
        _component(
            "Coefficient stability",
            coefficient_score,
            f"{coefficient_score:.1%} stability",
            "Agreement between pre-calibration and final Elastic Net coefficients.",
        ),
        _component(
            "Current-observation similarity",
            similarity_score,
            f"{nearest_similarity:.1%} nearest similarity",
            "Closeness to the nearest historical normalized factor vector.",
        ),
        _component(
            "Regime coverage",
            regime_coverage_score,
            f"{close_analog_count} close analogs",
            "Historical analogs with at least 90% normalized-factor similarity.",
        ),
    )
    return ReliabilityAssessment(
        model_reliability_score=float(model_score),
        model_reliability_label=_score_label(model_score),
        data_quality_score=float(data_score),
        data_quality_label=_score_label(data_score),
        current_distance_percentile=distance_percentile,
        current_distance_status=distance_status,
        nearest_similarity=float(nearest_similarity),
        close_analog_count=int(close_analog_count),
        components=components,
        correlated_factor_pairs=correlations,
        warnings=tuple(warnings),
    )


def _coefficient_stability(
    earlier: np.ndarray,
    later: np.ndarray,
) -> float:
    first = np.asarray(earlier, dtype=float)
    second = np.asarray(later, dtype=float)
    if first.shape != second.shape:
        raise ValueError("coefficient vectors must have matching shapes")
    denominator = float(np.linalg.norm(first) + np.linalg.norm(second))
    if denominator == 0:
        return 1.0
    return float(np.clip(1.0 - np.linalg.norm(first - second) / denominator, 0.0, 1.0))


def _correlated_factor_pairs(
    historical: pd.DataFrame,
    selected_factors: tuple[str, ...],
    threshold: float,
) -> tuple[FactorCorrelation, ...]:
    if len(selected_factors) < 2:
        return ()
    correlations = historical[list(selected_factors)].corr()
    pairs = []
    for left_index, factor_a in enumerate(selected_factors):
        for factor_b in selected_factors[left_index + 1 :]:
            correlation = float(correlations.loc[factor_a, factor_b])
            if np.isfinite(correlation) and abs(correlation) >= threshold:
                pairs.append(
                    FactorCorrelation(
                        factor_a=factor_a,
                        factor_b=factor_b,
                        correlation=correlation,
                    )
                )
    return tuple(
        sorted(
            pairs,
            key=lambda item: abs(item.correlation),
            reverse=True,
        )
    )


def _component(
    name: str,
    score: float,
    value: str,
    detail: str,
) -> ReliabilityComponent:
    if score >= 0.75:
        status = "Strong"
    elif score >= 0.50:
        status = "Watch"
    else:
        status = "Weak"
    return ReliabilityComponent(
        component=name,
        score=float(score * 100.0),
        status=status,
        value=value,
        detail=detail,
    )


def _score_label(score: float) -> str:
    if score >= 80:
        return "High"
    if score >= 60:
        return "Moderate"
    if score >= 40:
        return "Low"
    return "Very low"
