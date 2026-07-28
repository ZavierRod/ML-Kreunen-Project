"""Historical as-of snapshots with realized outcomes removed from inference."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from pandas.tseries.offsets import MonthEnd

from .benchmarks import relabel_training_panel

REPLAY_VERSION = "historical-replay-v1"
MONTH_COLUMN = "month_end"
SECURITY_COLUMN = "permno"
TARGET_COLUMN = "excess_return_next_month"
OUTCOME_COLUMNS = (
    "stock_return_next_month",
    "benchmark_return",
    "constituent_count",
    "total_lag_market_cap",
    TARGET_COLUMN,
)


@dataclass(frozen=True)
class ReplayOutcome:
    permno: int
    as_of_date: str
    target_month: str
    realized_excess_return: float
    realized_stock_return: float
    realized_benchmark_return: float
    benchmark_id: str


def available_as_of_dates(
    training: pd.DataFrame,
    latest_inference: pd.DataFrame,
    *,
    minimum_history_months: int = 120,
) -> tuple[pd.Timestamp, ...]:
    """Return replayable month ends plus the current inference month."""
    if minimum_history_months < 1:
        raise ValueError("minimum_history_months must be positive")
    _require_columns(training, {MONTH_COLUMN, TARGET_COLUMN}, "training")
    _require_columns(
        latest_inference,
        {MONTH_COLUMN, "target_month"},
        "latest inference",
    )
    training_dates = sorted(
        pd.to_datetime(
            training.loc[training[TARGET_COLUMN].notna(), MONTH_COLUMN]
        )
        .dt.to_period("M")
        .dt.to_timestamp("M")
        .unique()
    )
    replay_dates = training_dates[minimum_history_months:]
    latest_dates = (
        pd.to_datetime(latest_inference[MONTH_COLUMN])
        .dt.to_period("M")
        .dt.to_timestamp("M")
        .unique()
    )
    return tuple(
        pd.Timestamp(value)
        for value in sorted(set(replay_dates).union(latest_dates))
    )


def build_as_of_snapshot(
    training: pd.DataFrame,
    latest_inference: pd.DataFrame,
    as_of_date: str | pd.Timestamp,
) -> pd.DataFrame:
    """Build an inference cross-section without any realized target fields."""
    _require_columns(
        training,
        {
            SECURITY_COLUMN,
            MONTH_COLUMN,
            "target_month",
            "benchmark_id",
            TARGET_COLUMN,
        },
        "training",
    )
    _require_columns(
        latest_inference,
        {
            SECURITY_COLUMN,
            MONTH_COLUMN,
            "target_month",
            "benchmark_id",
            TARGET_COLUMN,
        },
        "latest inference",
    )
    as_of = _month_end(as_of_date)
    latest_dates = _normalize_months(latest_inference[MONTH_COLUMN])
    if (latest_dates == as_of).any():
        snapshot = latest_inference.loc[latest_dates == as_of].copy()
        source = "latest_inference"
    else:
        training_dates = _normalize_months(training[MONTH_COLUMN])
        snapshot = training.loc[training_dates == as_of].copy()
        source = "historical_replay"
    if snapshot.empty:
        raise ValueError(f"No cross-section is available for {as_of.date()}.")
    if snapshot.duplicated([SECURITY_COLUMN, MONTH_COLUMN]).any():
        raise ValueError("Replay snapshot contains duplicate security-month rows.")

    expected_target = as_of + MonthEnd(1)
    target_months = _normalize_months(snapshot["target_month"])
    if not (target_months == expected_target).all():
        raise ValueError("Replay target month is not the exact next calendar month.")

    for column in OUTCOME_COLUMNS:
        if column in snapshot.columns:
            snapshot[column] = np.nan
    if "label_status" in snapshot.columns:
        snapshot["label_status"] = (
            "inference"
            if source == "latest_inference"
            else "historical_replay_outcome_hidden"
        )
    snapshot.attrs["replay_version"] = REPLAY_VERSION
    snapshot.attrs["snapshot_source"] = source
    return snapshot.reset_index(drop=True)


def realized_replay_outcome(
    training: pd.DataFrame,
    permno: int,
    as_of_date: str | pd.Timestamp,
    benchmark_id: str | None = None,
) -> ReplayOutcome | None:
    """Return the held-back realized outcome for post-forecast evaluation."""
    _require_columns(
        training,
        {
            SECURITY_COLUMN,
            MONTH_COLUMN,
            "target_month",
            TARGET_COLUMN,
            "stock_return_next_month",
            "benchmark_return",
        },
        "training",
    )
    relabeled, selection = relabel_training_panel(
        training,
        benchmark_id,
    )
    as_of = _month_end(as_of_date)
    months = _normalize_months(relabeled[MONTH_COLUMN])
    row = relabeled.loc[
        (relabeled[SECURITY_COLUMN] == permno) & (months == as_of)
    ]
    if len(row) != 1 or pd.isna(row.iloc[0][TARGET_COLUMN]):
        return None
    item = row.iloc[0]
    return ReplayOutcome(
        permno=int(permno),
        as_of_date=as_of.date().isoformat(),
        target_month=_month_end(item["target_month"]).date().isoformat(),
        realized_excess_return=float(item[TARGET_COLUMN]),
        realized_stock_return=float(item["stock_return_next_month"]),
        realized_benchmark_return=float(item["benchmark_return"]),
        benchmark_id=selection.benchmark_id,
    )


def _month_end(value: object) -> pd.Timestamp:
    return pd.Timestamp(value).to_period("M").to_timestamp("M")


def _normalize_months(values: pd.Series) -> pd.Series:
    return (
        pd.to_datetime(values)
        .dt.to_period("M")
        .dt.to_timestamp("M")
    )


def _require_columns(
    frame: pd.DataFrame,
    required: set[str],
    name: str,
) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{name} is missing columns: {', '.join(missing)}")
