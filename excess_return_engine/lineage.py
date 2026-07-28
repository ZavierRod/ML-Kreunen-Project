"""Per-factor source lineage and point-in-time freshness assessment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import pandas as pd

from .features import (
    FACTOR_REGISTRY,
    FUNDAMENTAL_FACTOR_IDS,
    validate_factor_selection,
)

LINEAGE_VERSION = "factor-lineage-v1"
SOURCE_SYSTEM = "wrds-derived-research-panel"
FUNDAMENTAL_CURRENT_DAYS = 550
FUNDAMENTAL_STALE_DAYS = 730
MARKET_CURRENT_DAYS = 7


@dataclass(frozen=True)
class SourceValue:
    column: str
    value: float | str | None


@dataclass(frozen=True)
class FactorLineage:
    factor_id: str
    label: str
    category: str
    raw_value: float
    normalized_value: float | None
    source_system: str
    source_snapshot: str
    source_values: tuple[SourceValue, ...]
    observation_date: str
    period_end_date: str
    available_at: str
    age_days: int
    availability_lag_days: int
    freshness_status: str
    point_in_time_status: str
    availability_rule: str
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class FactorLineageAssessment:
    version: str
    as_of_date: str
    source_snapshot: str
    status: str
    freshness_score: float
    stale_factor_count: int
    aging_factor_count: int
    research_proxy_factor_count: int
    incomplete_factor_count: int
    factors: tuple[FactorLineage, ...]
    warnings: tuple[str, ...]


def assess_factor_lineage(
    current: pd.Series | Mapping[str, object],
    selected_factors: tuple[str, ...],
    as_of_date: str | pd.Timestamp,
    *,
    normalized_values: Mapping[str, float] | None = None,
    source_snapshot: str = "unversioned-research-panel",
    strict: bool = True,
) -> FactorLineageAssessment:
    """Trace selected current values to source fields and availability dates."""
    selected = validate_factor_selection(selected_factors)
    as_of = _month_end(as_of_date)
    normalized = normalized_values or {}
    factors = []
    assessment_warnings = []
    incomplete_count = 0

    for factor_id in selected:
        definition = FACTOR_REGISTRY[factor_id]
        raw_value = _numeric_value(_get(current, factor_id))
        supporting_columns = list(definition.source_columns)
        is_fundamental = factor_id in FUNDAMENTAL_FACTOR_IDS
        date_columns = (
            ("datadate", "fund_available_date")
            if is_fundamental
            else ("source_last_trading_date",)
        )
        for column in date_columns:
            if column not in supporting_columns:
                supporting_columns.append(column)

        missing_columns = [
            column
            for column in supporting_columns
            if not _has_key(current, column)
        ]
        missing_values = [
            column
            for column in supporting_columns
            if _has_key(current, column)
            and _is_missing(_get(current, column))
        ]
        warnings = []
        if raw_value is None:
            warnings.append("The selected factor value is missing.")
        if missing_columns:
            warnings.append(
                "Missing source columns: " + ", ".join(missing_columns) + "."
            )
        if missing_values:
            warnings.append(
                "Missing source values: " + ", ".join(missing_values) + "."
            )

        if is_fundamental:
            period_end = _timestamp_value(_get(current, "datadate"))
            available_at = _timestamp_value(
                _get(current, "fund_available_date")
            )
            observation = period_end
            point_in_time_status = "research_lag_proxy"
            warnings.append(
                "Availability uses the documented fixed-lag research proxy."
            )
        else:
            observation = _timestamp_value(
                _get(current, "source_last_trading_date")
            )
            period_end = observation
            available_at = as_of
            point_in_time_status = "month_end_observed"

        invalid_date = (
            period_end is None
            or available_at is None
            or observation is None
        )
        future_dated = (
            not invalid_date
            and (
                period_end > as_of
                or available_at > as_of
                or observation > as_of
            )
        )
        if invalid_date:
            warnings.append("Required source dates are unavailable.")
        if future_dated:
            warnings.append(
                "Source evidence was not available by the forecast as-of date."
            )

        incomplete = (
            raw_value is None
            or bool(missing_columns)
            or bool(missing_values)
            or invalid_date
            or future_dated
        )
        if incomplete:
            incomplete_count += 1
            freshness_status = "Incomplete"
            age_days = -1
            availability_lag_days = -1
        else:
            assert period_end is not None
            assert available_at is not None
            age_days = int((as_of - period_end).days)
            availability_lag_days = int((available_at - period_end).days)
            freshness_status = _freshness_status(
                is_fundamental,
                age_days,
            )
            if freshness_status == "Aging":
                warnings.append(
                    "The underlying fundamental period is more than "
                    f"{FUNDAMENTAL_CURRENT_DAYS} days old."
                )
            elif freshness_status == "Stale":
                warnings.append(
                    "The underlying source period exceeds the freshness limit."
                )

        factor = FactorLineage(
            factor_id=factor_id,
            label=definition.label,
            category=definition.category,
            raw_value=float("nan") if raw_value is None else raw_value,
            normalized_value=(
                None
                if factor_id not in normalized
                else float(normalized[factor_id])
            ),
            source_system=SOURCE_SYSTEM,
            source_snapshot=source_snapshot,
            source_values=tuple(
                SourceValue(
                    column=column,
                    value=_serializable_value(_get(current, column)),
                )
                for column in supporting_columns
            ),
            observation_date=_date_string(observation),
            period_end_date=_date_string(period_end),
            available_at=_date_string(available_at),
            age_days=age_days,
            availability_lag_days=availability_lag_days,
            freshness_status=freshness_status,
            point_in_time_status=point_in_time_status,
            availability_rule=definition.availability_rule,
            warnings=tuple(warnings),
        )
        factors.append(factor)
        assessment_warnings.extend(
            f"{definition.label}: {warning}" for warning in warnings
        )

    if strict and incomplete_count:
        raise ValueError(
            "Selected factor lineage is incomplete: "
            + " ".join(assessment_warnings)
        )
    stale_count = sum(
        factor.freshness_status == "Stale" for factor in factors
    )
    aging_count = sum(
        factor.freshness_status == "Aging" for factor in factors
    )
    proxy_count = sum(
        factor.point_in_time_status == "research_lag_proxy"
        for factor in factors
    )
    freshness_scores = [
        {
            "Current": 1.0,
            "Aging": 0.6,
            "Stale": 0.0,
            "Incomplete": 0.0,
        }[factor.freshness_status]
        for factor in factors
    ]
    if incomplete_count:
        status = "Incomplete"
    elif stale_count:
        status = "Stale"
    elif aging_count:
        status = "Aging"
    elif proxy_count:
        status = "Research lag proxy"
    else:
        status = "Verified"
    return FactorLineageAssessment(
        version=LINEAGE_VERSION,
        as_of_date=as_of.date().isoformat(),
        source_snapshot=source_snapshot,
        status=status,
        freshness_score=float(np.mean(freshness_scores)),
        stale_factor_count=stale_count,
        aging_factor_count=aging_count,
        research_proxy_factor_count=proxy_count,
        incomplete_factor_count=incomplete_count,
        factors=tuple(factors),
        warnings=tuple(assessment_warnings),
    )


def _freshness_status(is_fundamental: bool, age_days: int) -> str:
    if is_fundamental:
        if age_days <= FUNDAMENTAL_CURRENT_DAYS:
            return "Current"
        if age_days <= FUNDAMENTAL_STALE_DAYS:
            return "Aging"
        return "Stale"
    return "Current" if age_days <= MARKET_CURRENT_DAYS else "Stale"


def _has_key(row: pd.Series | Mapping[str, object], key: str) -> bool:
    return key in row


def _get(
    row: pd.Series | Mapping[str, object],
    key: str,
) -> object:
    return row.get(key)


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    missing = pd.isna(value)
    return bool(missing) if np.isscalar(missing) else False


def _numeric_value(value: object) -> float | None:
    if _is_missing(value):
        return None
    numeric = float(value)
    return numeric if np.isfinite(numeric) else None


def _timestamp_value(value: object) -> pd.Timestamp | None:
    if _is_missing(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    parsed = pd.Timestamp(parsed)
    return parsed.to_period("D").to_timestamp()


def _month_end(value: object) -> pd.Timestamp:
    return pd.Timestamp(value).to_period("M").to_timestamp("M")


def _date_string(value: pd.Timestamp | None) -> str:
    return "" if value is None else value.date().isoformat()


def _serializable_value(value: object) -> float | str | None:
    if _is_missing(value):
        return None
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return pd.Timestamp(value).date().isoformat()
    if isinstance(value, (int, float, np.integer, np.floating)):
        numeric = float(value)
        return numeric if np.isfinite(numeric) else None
    return str(value)
