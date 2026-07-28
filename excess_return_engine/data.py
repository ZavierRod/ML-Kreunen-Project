"""Local WRDS panel adapter and calendar-safe excess-return labels."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from pandas.tseries.offsets import MonthEnd

DATA_DIR_ENV = "WRDS_RESEARCH_DATA_DIR"
MONTHLY_PANEL_FILENAME = "monthly_panel.parquet"

SECURITY_COLUMN = "permno"
MONTH_COLUMN = "month_end"
RETURN_COLUMN = "ret_m"
MARKET_CAP_COLUMN = "market_cap"

LEGACY_TARGET_COLUMNS = {"y_next"}
REQUIRED_STOCK_COLUMNS = {
    SECURITY_COLUMN,
    MONTH_COLUMN,
    RETURN_COLUMN,
    MARKET_CAP_COLUMN,
}
REQUIRED_BENCHMARK_COLUMNS = {
    MONTH_COLUMN,
    "benchmark_id",
    "benchmark_return",
}


@dataclass(frozen=True)
class ExcessReturnPanels:
    """Outputs from an exact-calendar-month label build."""

    training: pd.DataFrame
    inference: pd.DataFrame
    unresolved: pd.DataFrame

    @property
    def summary(self) -> dict[str, object]:
        as_of_min = self.training[MONTH_COLUMN].min() if not self.training.empty else None
        as_of_max = self.training[MONTH_COLUMN].max() if not self.training.empty else None
        return {
            "training_rows": len(self.training),
            "inference_rows": len(self.inference),
            "unresolved_rows": len(self.unresolved),
            "training_start": _date_string(as_of_min),
            "training_end": _date_string(as_of_max),
        }


def _date_string(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).date().isoformat()


def _require_columns(
    frame: pd.DataFrame, required: Iterable[str], frame_name: str
) -> None:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"{frame_name} is missing columns: {', '.join(missing)}")


def _normalize_month_end(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values, errors="coerce")
    if parsed.isna().any():
        bad_count = int(parsed.isna().sum())
        raise ValueError(f"month_end contains {bad_count} invalid date value(s)")
    return parsed.dt.to_period("M").dt.to_timestamp("M")


def _validate_unique_security_months(frame: pd.DataFrame) -> None:
    duplicate = frame.duplicated([SECURITY_COLUMN, MONTH_COLUMN], keep=False)
    if duplicate.any():
        example = frame.loc[duplicate, [SECURITY_COLUMN, MONTH_COLUMN]].iloc[0]
        raise ValueError(
            "stock panel contains duplicate security-month rows; "
            f"example: permno={example[SECURITY_COLUMN]}, "
            f"month_end={_date_string(example[MONTH_COLUMN])}"
        )


def resolve_monthly_panel_path(data_dir: str | Path | None = None) -> Path:
    """Resolve a local monthly panel without hardcoding a licensed-data path."""
    configured = data_dir or os.getenv(DATA_DIR_ENV)
    if not configured:
        raise FileNotFoundError(
            f"Set {DATA_DIR_ENV} to DatasetKreunenTest or its artifacts directory."
        )

    base = Path(configured).expanduser().resolve()
    candidates = (
        base / MONTHLY_PANEL_FILENAME,
        base / "artifacts" / MONTHLY_PANEL_FILENAME,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    searched = ", ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"Could not find {MONTHLY_PANEL_FILENAME}; searched {searched}")


def load_wrds_monthly_panel(
    data_dir: str | Path | None = None,
    columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Load the local research panel while keeping WRDS data outside this repo."""
    path = resolve_monthly_panel_path(data_dir)
    selected = list(columns) if columns is not None else None
    panel = pd.read_parquet(path, columns=selected)
    _require_columns(panel, REQUIRED_STOCK_COLUMNS, "stock panel")
    panel = panel.copy()
    panel[MONTH_COLUMN] = _normalize_month_end(panel[MONTH_COLUMN])
    _validate_unique_security_months(panel)
    return panel.sort_values([SECURITY_COLUMN, MONTH_COLUMN]).reset_index(drop=True)


def build_lagged_value_weighted_benchmark(
    stock_panel: pd.DataFrame,
    benchmark_id: str = "wrds-universe-lagged-vw",
) -> pd.DataFrame:
    """Build a research benchmark using prior-month market-cap weights.

    A security contributes to month t only when its prior observation is exactly
    month t-1. This prevents a stale market cap from crossing a listing gap.
    """
    _require_columns(stock_panel, REQUIRED_STOCK_COLUMNS, "stock panel")
    panel = stock_panel[
        [SECURITY_COLUMN, MONTH_COLUMN, RETURN_COLUMN, MARKET_CAP_COLUMN]
    ].copy()
    panel[MONTH_COLUMN] = _normalize_month_end(panel[MONTH_COLUMN])
    _validate_unique_security_months(panel)
    panel = panel.sort_values([SECURITY_COLUMN, MONTH_COLUMN])

    grouped = panel.groupby(SECURITY_COLUMN, sort=False)
    panel["previous_month"] = grouped[MONTH_COLUMN].shift(1)
    panel["lag_market_cap"] = grouped[MARKET_CAP_COLUMN].shift(1)
    expected_month = panel["previous_month"] + MonthEnd(1)
    panel.loc[panel[MONTH_COLUMN] != expected_month, "lag_market_cap"] = np.nan

    returns = pd.to_numeric(panel[RETURN_COLUMN], errors="coerce")
    weights = pd.to_numeric(panel["lag_market_cap"], errors="coerce")
    eligible = returns.notna() & np.isfinite(returns) & weights.notna() & (weights > 0)
    weighted = panel.loc[eligible, [MONTH_COLUMN]].copy()
    weighted["weighted_return"] = returns.loc[eligible] * weights.loc[eligible]
    weighted["lag_market_cap"] = weights.loc[eligible]

    if weighted.empty:
        return pd.DataFrame(
            columns=[
                MONTH_COLUMN,
                "benchmark_id",
                "benchmark_return",
                "constituent_count",
                "total_lag_market_cap",
            ]
        )

    benchmark = (
        weighted.groupby(MONTH_COLUMN, as_index=False)
        .agg(
            weighted_return=("weighted_return", "sum"),
            total_lag_market_cap=("lag_market_cap", "sum"),
            constituent_count=("lag_market_cap", "size"),
        )
        .sort_values(MONTH_COLUMN)
    )
    benchmark["benchmark_return"] = (
        benchmark["weighted_return"] / benchmark["total_lag_market_cap"]
    )
    benchmark["benchmark_id"] = benchmark_id
    return benchmark[
        [
            MONTH_COLUMN,
            "benchmark_id",
            "benchmark_return",
            "constituent_count",
            "total_lag_market_cap",
        ]
    ].reset_index(drop=True)


def build_excess_return_panels(
    stock_panel: pd.DataFrame,
    benchmark_panel: pd.DataFrame,
) -> ExcessReturnPanels:
    """Create exact-next-month training, inference, and unresolved panels."""
    _require_columns(stock_panel, REQUIRED_STOCK_COLUMNS, "stock panel")
    _require_columns(benchmark_panel, REQUIRED_BENCHMARK_COLUMNS, "benchmark panel")

    stock = stock_panel.drop(
        columns=[column for column in LEGACY_TARGET_COLUMNS if column in stock_panel],
        errors="ignore",
    ).copy()
    stock[MONTH_COLUMN] = _normalize_month_end(stock[MONTH_COLUMN])
    _validate_unique_security_months(stock)
    stock = stock.sort_values([SECURITY_COLUMN, MONTH_COLUMN]).reset_index(drop=True)

    benchmark = benchmark_panel.copy()
    benchmark[MONTH_COLUMN] = _normalize_month_end(benchmark[MONTH_COLUMN])
    if benchmark.duplicated([MONTH_COLUMN, "benchmark_id"]).any():
        raise ValueError("benchmark panel contains duplicate month_end/benchmark_id rows")
    benchmark_ids = benchmark["benchmark_id"].dropna().astype(str).unique()
    if len(benchmark_ids) != 1:
        raise ValueError("benchmark panel must contain exactly one benchmark_id")

    features = stock.copy()
    features["target_month"] = features[MONTH_COLUMN] + MonthEnd(1)
    outcomes = stock[[SECURITY_COLUMN, MONTH_COLUMN, RETURN_COLUMN]].rename(
        columns={
            MONTH_COLUMN: "target_month",
            RETURN_COLUMN: "stock_return_next_month",
        }
    )
    labeled = features.merge(
        outcomes,
        on=[SECURITY_COLUMN, "target_month"],
        how="left",
        validate="one_to_one",
    )

    benchmark_for_join = benchmark.rename(columns={MONTH_COLUMN: "target_month"})
    labeled = labeled.merge(
        benchmark_for_join,
        on="target_month",
        how="left",
        validate="many_to_one",
    )

    stock_available = labeled["stock_return_next_month"].notna()
    benchmark_available = labeled["benchmark_return"].notna()
    labeled["label_status"] = np.select(
        [
            stock_available & benchmark_available,
            ~stock_available & benchmark_available,
            stock_available & ~benchmark_available,
        ],
        [
            "complete",
            "missing_stock_return",
            "missing_benchmark_return",
        ],
        default="missing_stock_and_benchmark_return",
    )
    labeled["excess_return_next_month"] = (
        labeled["stock_return_next_month"] - labeled["benchmark_return"]
    )

    training = labeled[labeled["label_status"] == "complete"].copy()
    unresolved = labeled[labeled["label_status"] != "complete"].copy()
    latest_as_of = labeled[MONTH_COLUMN].max()
    inference = unresolved[unresolved[MONTH_COLUMN] == latest_as_of].copy()

    sort_columns = [MONTH_COLUMN, SECURITY_COLUMN]
    return ExcessReturnPanels(
        training=training.sort_values(sort_columns).reset_index(drop=True),
        inference=inference.sort_values(sort_columns).reset_index(drop=True),
        unresolved=unresolved.sort_values(sort_columns).reset_index(drop=True),
    )


def build_local_research_artifacts(
    data_dir: str | Path | None,
    output_dir: str | Path,
) -> ExcessReturnPanels:
    """Build local Parquet artifacts that are excluded from version control."""
    stock = load_wrds_monthly_panel(data_dir)
    benchmark = build_lagged_value_weighted_benchmark(stock)
    panels = build_excess_return_panels(stock, benchmark)

    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    benchmark.to_parquet(destination / "benchmark_returns.parquet", index=False)
    panels.training.to_parquet(destination / "training_panel.parquet", index=False)
    panels.inference.to_parquet(destination / "inference_panel.parquet", index=False)
    panels.unresolved.to_parquet(destination / "unresolved_labels.parquet", index=False)
    return panels


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build calendar-safe local excess-return research panels."
    )
    parser.add_argument(
        "--data-dir",
        help=f"DatasetKreunenTest root or artifacts directory; defaults to {DATA_DIR_ENV}.",
    )
    parser.add_argument(
        "--output-dir",
        default="local_artifacts/excess_return_engine",
        help="Local output directory (excluded from git).",
    )
    args = parser.parse_args()

    panels = build_local_research_artifacts(args.data_dir, args.output_dir)
    for key, value in panels.summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
