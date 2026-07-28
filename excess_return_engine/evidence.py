"""Deterministic factor-regime and historical-analog evidence."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FactorRegime:
    factor_id: str
    normalized_value: float
    percentile: float
    regime: str


@dataclass(frozen=True)
class HistoricalAnalog:
    permno: int
    ticker: str | None
    company: str | None
    month_end: str
    target_month: str
    similarity: float
    observed_excess_return: float


@dataclass(frozen=True)
class HistoricalEvidence:
    neighbor_count: int
    mean_excess_return: float
    median_excess_return: float
    probability_positive: float
    tenth_percentile: float
    ninetieth_percentile: float
    analogs: tuple[HistoricalAnalog, ...]


def classify_factor_regimes(
    selected_factors: tuple[str, ...],
    normalized_values: np.ndarray,
) -> tuple[FactorRegime, ...]:
    """Map cross-sectional ranks to explicit percentile buckets."""
    values = np.asarray(normalized_values, dtype=float)
    if values.ndim != 1 or len(values) != len(selected_factors):
        raise ValueError("normalized_values must match selected_factors")

    regimes = []
    for factor_id, value in zip(selected_factors, values):
        percentile = float(np.clip((value + 1.0) / 2.0, 0.0, 1.0))
        if percentile <= 0.20:
            regime = "Bottom quintile"
        elif percentile <= 0.40:
            regime = "Below median"
        elif percentile < 0.60:
            regime = "Near median"
        elif percentile < 0.80:
            regime = "Above median"
        else:
            regime = "Top quintile"
        regimes.append(
            FactorRegime(
                factor_id=factor_id,
                normalized_value=float(value),
                percentile=percentile,
                regime=regime,
            )
        )
    return tuple(regimes)


def find_similar_conditions(
    historical: pd.DataFrame,
    selected_factors: tuple[str, ...],
    normalized_values: np.ndarray,
    neighbor_count: int,
    target_column: str,
) -> HistoricalEvidence:
    """Find nearest historical rows in normalized selected-factor space."""
    if neighbor_count < 1:
        raise ValueError("neighbor_count must be positive")
    required = {"permno", "month_end", target_column, *selected_factors}
    missing = sorted(required - set(historical.columns))
    if missing:
        raise ValueError(
            f"historical evidence is missing columns: {', '.join(missing)}"
        )

    current = np.asarray(normalized_values, dtype=np.float32)
    if current.ndim != 1 or len(current) != len(selected_factors):
        raise ValueError("normalized_values must match selected_factors")

    candidates = historical.dropna(
        subset=[target_column, *selected_factors]
    ).reset_index(drop=True)
    if candidates.empty:
        raise ValueError("No complete historical rows are available for analogs.")

    matrix = candidates[list(selected_factors)].to_numpy(dtype=np.float32)
    distances = np.sqrt(np.mean(np.square(matrix - current), axis=1))
    count = min(neighbor_count, len(candidates))
    nearest = np.argpartition(distances, count - 1)[:count]
    nearest = nearest[np.argsort(distances[nearest], kind="stable")]

    outcomes = candidates.iloc[nearest][target_column].to_numpy(dtype=float)
    analogs = []
    for row_index, distance in zip(nearest, distances[nearest]):
        row = candidates.iloc[int(row_index)]
        month_end = pd.Timestamp(row["month_end"])
        target_month = (
            pd.Timestamp(row["target_month"])
            if "target_month" in candidates.columns
            else month_end + pd.offsets.MonthEnd(1)
        )
        analogs.append(
            HistoricalAnalog(
                permno=int(row["permno"]),
                ticker=_optional_string(row.get("ticker")),
                company=_optional_string(row.get("company")),
                month_end=month_end.date().isoformat(),
                target_month=target_month.date().isoformat(),
                similarity=float(np.clip(1.0 - float(distance) / 2.0, 0.0, 1.0)),
                observed_excess_return=float(row[target_column]),
            )
        )

    return HistoricalEvidence(
        neighbor_count=count,
        mean_excess_return=float(np.mean(outcomes)),
        median_excess_return=float(np.median(outcomes)),
        probability_positive=float(np.mean(outcomes > 0)),
        tenth_percentile=float(np.quantile(outcomes, 0.10)),
        ninetieth_percentile=float(np.quantile(outcomes, 0.90)),
        analogs=tuple(analogs),
    )


def _optional_string(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(value)
