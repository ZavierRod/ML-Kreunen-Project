"""Versioned benchmark registry and benchmark-consistent target relabeling."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

BENCHMARK_VERSION = "benchmark-registry-v1"
LAGGED_VALUE_WEIGHTED_BENCHMARK_ID = "wrds-universe-lagged-vw"
EQUAL_WEIGHT_BENCHMARK_ID = "wrds-universe-equal-weight"


@dataclass(frozen=True)
class BenchmarkDefinition:
    benchmark_id: str
    label: str
    method: str
    limitation: str


@dataclass(frozen=True)
class BenchmarkSelection:
    version: str
    benchmark_id: str
    label: str
    method: str
    limitation: str


def benchmark_options(
    source_benchmark_id: str,
) -> tuple[BenchmarkDefinition, ...]:
    """Return the source benchmark and supported derived alternatives."""
    if source_benchmark_id == LAGGED_VALUE_WEIGHTED_BENCHMARK_ID:
        source_label = "Lagged-cap-weighted covered universe"
        source_method = (
            "Covered-universe monthly return weighted by each security's "
            "exact prior-calendar-month market capitalization."
        )
        source_limitation = (
            "Research benchmark derived from the covered WRDS universe; "
            "it is not a licensed CRSP index series."
        )
    else:
        source_label = f"Source benchmark · {source_benchmark_id}"
        source_method = (
            "Precomputed source-panel benchmark preserved without relabeling."
        )
        source_limitation = (
            "Benchmark methodology must be verified against the source-panel "
            "data contract."
        )
    return (
        BenchmarkDefinition(
            benchmark_id=source_benchmark_id,
            label=source_label,
            method=source_method,
            limitation=source_limitation,
        ),
        BenchmarkDefinition(
            benchmark_id=EQUAL_WEIGHT_BENCHMARK_ID,
            label="Equal-weighted covered universe",
            method=(
                "Arithmetic mean of eligible covered-security returns for "
                "each realized target month."
            ),
            limitation=(
                "Research benchmark derived from securities represented in "
                "the labeled panel; newly listed or unresolved rows may be "
                "absent."
            ),
        ),
    )


def select_benchmark(
    source_benchmark_id: str,
    requested_benchmark_id: str | None,
) -> BenchmarkSelection:
    benchmark_id = requested_benchmark_id or source_benchmark_id
    definitions = {
        item.benchmark_id: item
        for item in benchmark_options(source_benchmark_id)
    }
    if benchmark_id not in definitions:
        raise ValueError(f"Unsupported benchmark: {benchmark_id}.")
    definition = definitions[benchmark_id]
    return BenchmarkSelection(
        version=BENCHMARK_VERSION,
        benchmark_id=definition.benchmark_id,
        label=definition.label,
        method=definition.method,
        limitation=definition.limitation,
    )


def relabel_forecast_panels(
    training: pd.DataFrame,
    inference: pd.DataFrame,
    requested_benchmark_id: str | None,
) -> tuple[pd.DataFrame, pd.DataFrame, BenchmarkSelection]:
    """Recompute excess-return labels for the selected benchmark."""
    required_training = {
        "target_month",
        "stock_return_next_month",
        "benchmark_id",
        "benchmark_return",
        "excess_return_next_month",
    }
    required_inference = {
        "target_month",
        "benchmark_id",
        "benchmark_return",
        "excess_return_next_month",
    }
    _require_columns(training, required_training, "training panel")
    _require_columns(inference, required_inference, "inference panel")
    source_ids = set(training["benchmark_id"].dropna().astype(str))
    inference_source_ids = set(
        inference["benchmark_id"].dropna().astype(str)
    )
    if len(source_ids) != 1 or inference_source_ids != source_ids:
        raise ValueError(
            "Source training and inference panels must use one benchmark."
        )
    relabeled_training, selection = relabel_training_panel(
        training,
        requested_benchmark_id,
    )
    relabeled_inference = inference.copy()
    if selection.benchmark_id == next(iter(source_ids)):
        return relabeled_training, relabeled_inference, selection
    relabeled_inference["benchmark_id"] = selection.benchmark_id
    for column in (
        "benchmark_return",
        "constituent_count",
        "total_lag_market_cap",
        "excess_return_next_month",
    ):
        if column in relabeled_inference:
            relabeled_inference[column] = np.nan
    return relabeled_training, relabeled_inference, selection


def relabel_training_panel(
    training: pd.DataFrame,
    requested_benchmark_id: str | None,
) -> tuple[pd.DataFrame, BenchmarkSelection]:
    """Relabel realized outcomes for replay and forecast training."""
    required = {
        "target_month",
        "stock_return_next_month",
        "benchmark_id",
        "benchmark_return",
        "excess_return_next_month",
    }
    _require_columns(training, required, "training panel")
    source_ids = set(training["benchmark_id"].dropna().astype(str))
    if len(source_ids) != 1:
        raise ValueError("Training panel must use one source benchmark.")
    source_id = next(iter(source_ids))
    selection = select_benchmark(source_id, requested_benchmark_id)
    relabeled = training.copy()
    if selection.benchmark_id == source_id:
        return relabeled, selection

    stock_returns = pd.to_numeric(
        relabeled["stock_return_next_month"],
        errors="coerce",
    )
    eligible = stock_returns.notna() & np.isfinite(stock_returns)
    benchmark = (
        relabeled.loc[eligible, ["target_month"]]
        .assign(_stock_return=stock_returns.loc[eligible])
        .groupby("target_month", sort=False)["_stock_return"]
        .agg(["mean", "size"])
    )
    benchmark_return = relabeled["target_month"].map(benchmark["mean"])
    if benchmark_return.isna().any():
        raise ValueError(
            "Equal-weight benchmark could not be resolved for every "
            "training target month."
        )
    relabeled["benchmark_id"] = selection.benchmark_id
    relabeled["benchmark_return"] = benchmark_return
    relabeled["constituent_count"] = relabeled["target_month"].map(
        benchmark["size"]
    )
    relabeled["total_lag_market_cap"] = np.nan
    relabeled["excess_return_next_month"] = (
        stock_returns - benchmark_return
    )
    return relabeled, selection


def _require_columns(
    frame: pd.DataFrame,
    required: set[str],
    frame_name: str,
) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(
            f"{frame_name} is missing columns: {', '.join(missing)}"
        )
