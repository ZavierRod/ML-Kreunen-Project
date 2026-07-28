"""Memory-efficient monthly panel rebuild from the enriched daily WRDS source."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

SECURITY_COLUMN = "permno"
DATE_COLUMN = "dlycaldt"
RETURN_COLUMN = "dlyret"
PRICE_COLUMN = "dlyprc"
MONTH_COLUMN = "month_end"

LAST_VALUE_COLUMNS = [
    "gvkey",
    "company",
    "ticker",
    "dlyprc",
    "dlyvol",
    "market_cap",
    "datadate",
    "fund_available_date",
    "ceq",
    "momentum_12_1",
    "volatility_21d",
    "liquidity_21d",
    "asset_growth",
    "leverage",
    "profit_margin",
    "roe",
    "ev",
    "ev_ebitda",
]
REQUIRED_DAILY_COLUMNS = {
    SECURITY_COLUMN,
    DATE_COLUMN,
    RETURN_COLUMN,
    PRICE_COLUMN,
    *LAST_VALUE_COLUMNS,
}
PARTIAL_SUM_COLUMNS = ["log_ret_sum", "n_days"]
PARTIAL_DATE_COLUMN = "partial_last_trading_date"


def _require_columns(
    frame: pd.DataFrame, required: Iterable[str], frame_name: str
) -> None:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"{frame_name} is missing columns: {', '.join(missing)}")


def aggregate_daily_chunk(
    daily: pd.DataFrame,
    min_price: float = 5.0,
) -> pd.DataFrame:
    """Aggregate one daily-data chunk into mergeable security-month fragments."""
    _require_columns(daily, REQUIRED_DAILY_COLUMNS, "daily panel")
    chunk = daily.copy()
    chunk[DATE_COLUMN] = pd.to_datetime(chunk[DATE_COLUMN], errors="coerce")
    numeric_return = pd.to_numeric(chunk[RETURN_COLUMN], errors="coerce")
    numeric_price = pd.to_numeric(chunk[PRICE_COLUMN], errors="coerce")
    eligible = (
        chunk[DATE_COLUMN].notna()
        & numeric_return.notna()
        & np.isfinite(numeric_return)
        & numeric_price.abs().ge(min_price)
    )
    chunk = chunk.loc[eligible].copy()
    if chunk.empty:
        return _empty_partial_panel()

    chunk[RETURN_COLUMN] = numeric_return.loc[eligible]
    chunk[MONTH_COLUMN] = (
        chunk[DATE_COLUMN].dt.to_period("M").dt.to_timestamp("M")
    )
    chunk["log_return"] = np.log1p(chunk[RETURN_COLUMN].clip(lower=-0.99))
    chunk = chunk.sort_values([SECURITY_COLUMN, DATE_COLUMN])

    keys = [SECURITY_COLUMN, MONTH_COLUMN]
    grouped = chunk.groupby(keys, sort=False)
    sums = grouped["log_return"].agg(log_ret_sum="sum", n_days="size")
    last_values = grouped[LAST_VALUE_COLUMNS].last()
    last_dates = grouped[DATE_COLUMN].max().rename(PARTIAL_DATE_COLUMN)
    return (
        pd.concat([sums, last_dates, last_values], axis=1)
        .reset_index()
        .sort_values(keys)
        .reset_index(drop=True)
    )


def _empty_partial_panel() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            SECURITY_COLUMN,
            MONTH_COLUMN,
            *PARTIAL_SUM_COLUMNS,
            PARTIAL_DATE_COLUMN,
            *LAST_VALUE_COLUMNS,
        ]
    )


def combine_monthly_fragments(
    fragments: Iterable[pd.DataFrame],
    min_trading_days: int = 5,
) -> pd.DataFrame:
    """Combine row-group fragments and retain every observed security month."""
    nonempty = [fragment for fragment in fragments if not fragment.empty]
    if not nonempty:
        return pd.DataFrame(
            columns=[
                SECURITY_COLUMN,
                "month",
                MONTH_COLUMN,
                "log_ret_m",
                "ret_m",
                "n_days",
                "source_last_trading_date",
                *LAST_VALUE_COLUMNS,
            ]
        )

    partial = pd.concat(nonempty, ignore_index=True)
    required = {
        SECURITY_COLUMN,
        MONTH_COLUMN,
        *PARTIAL_SUM_COLUMNS,
        PARTIAL_DATE_COLUMN,
        *LAST_VALUE_COLUMNS,
    }
    _require_columns(partial, required, "monthly fragments")
    partial[MONTH_COLUMN] = pd.to_datetime(partial[MONTH_COLUMN])
    partial[PARTIAL_DATE_COLUMN] = pd.to_datetime(partial[PARTIAL_DATE_COLUMN])
    partial = partial.sort_values(
        [SECURITY_COLUMN, MONTH_COLUMN, PARTIAL_DATE_COLUMN]
    )

    keys = [SECURITY_COLUMN, MONTH_COLUMN]
    grouped = partial.groupby(keys, sort=False)
    sums = grouped[PARTIAL_SUM_COLUMNS].sum()
    last_values = grouped[LAST_VALUE_COLUMNS].last()
    last_dates = grouped[PARTIAL_DATE_COLUMN].max().rename(
        "source_last_trading_date"
    )
    monthly = pd.concat([sums, last_dates, last_values], axis=1).reset_index()
    monthly = monthly[monthly["n_days"] >= min_trading_days].copy()
    monthly["log_ret_m"] = monthly["log_ret_sum"]
    monthly["ret_m"] = np.expm1(monthly["log_ret_m"])
    monthly["month"] = monthly[MONTH_COLUMN].dt.to_period("M").astype(str)

    output_columns = [
        SECURITY_COLUMN,
        "month",
        MONTH_COLUMN,
        "log_ret_m",
        "ret_m",
        "n_days",
        "source_last_trading_date",
        *LAST_VALUE_COLUMNS,
    ]
    return (
        monthly[output_columns]
        .sort_values([SECURITY_COLUMN, MONTH_COLUMN])
        .reset_index(drop=True)
    )


def build_monthly_panel_from_parquet(
    daily_path: str | Path,
    min_price: float = 5.0,
    min_trading_days: int = 5,
) -> pd.DataFrame:
    """Read one Parquet row group at a time and return a full monthly panel."""
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - dependency error is environment-specific.
        raise RuntimeError(
            "pyarrow is required to rebuild the WRDS monthly panel. "
            "Install requirements.txt first."
        ) from exc

    source = Path(daily_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Missing enriched daily panel: {source}")

    parquet = pq.ParquetFile(source)
    available = set(parquet.schema_arrow.names)
    missing = sorted(REQUIRED_DAILY_COLUMNS - available)
    if missing:
        raise ValueError(f"daily Parquet is missing columns: {', '.join(missing)}")

    read_columns = list(
        dict.fromkeys(
            [
                SECURITY_COLUMN,
                DATE_COLUMN,
                RETURN_COLUMN,
                PRICE_COLUMN,
                *LAST_VALUE_COLUMNS,
            ]
        )
    )
    fragments = []
    for row_group in range(parquet.metadata.num_row_groups):
        daily = parquet.read_row_group(row_group, columns=read_columns).to_pandas()
        fragments.append(aggregate_daily_chunk(daily, min_price=min_price))

    return combine_monthly_fragments(
        fragments,
        min_trading_days=min_trading_days,
    )


def write_monthly_panel(
    daily_path: str | Path,
    output_path: str | Path,
    min_price: float = 5.0,
    min_trading_days: int = 5,
) -> pd.DataFrame:
    """Build and persist the retained-final-row monthly research panel."""
    monthly = build_monthly_panel_from_parquet(
        daily_path,
        min_price=min_price,
        min_trading_days=min_trading_days,
    )
    destination = Path(output_path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    monthly.to_parquet(destination, index=False)
    return monthly


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild a monthly panel while retaining final security months."
    )
    parser.add_argument("--daily-path", required=True)
    parser.add_argument(
        "--output-path",
        default="local_artifacts/excess_return_engine/monthly_panel_full.parquet",
    )
    parser.add_argument("--min-price", type=float, default=5.0)
    parser.add_argument("--min-trading-days", type=int, default=5)
    args = parser.parse_args()

    monthly = write_monthly_panel(
        args.daily_path,
        args.output_path,
        min_price=args.min_price,
        min_trading_days=args.min_trading_days,
    )
    print(f"rows: {len(monthly)}")
    print(f"securities: {monthly[SECURITY_COLUMN].nunique()}")
    print(
        "months: "
        f"{monthly[MONTH_COLUMN].min().date()} through "
        f"{monthly[MONTH_COLUMN].max().date()}"
    )
    print(f"output: {Path(args.output_path).expanduser().resolve()}")


if __name__ == "__main__":
    main()
