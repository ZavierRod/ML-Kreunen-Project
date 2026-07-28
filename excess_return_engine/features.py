"""Versioned factor registry and calendar-safe monthly feature engineering."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from pandas.tseries.offsets import MonthEnd

FEATURE_VERSION = "wrds-us-equity-v1"
SECURITY_COLUMN = "permno"
MONTH_COLUMN = "month_end"
RANK_SUFFIX = "__rank"


@dataclass(frozen=True)
class FactorDefinition:
    factor_id: str
    label: str
    category: str
    description: str
    source_columns: tuple[str, ...]
    availability_rule: str
    version: str = FEATURE_VERSION

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


FACTOR_DEFINITIONS = (
    FactorDefinition(
        "momentum_12_1",
        "12-1 momentum",
        "Momentum",
        "Cumulative price momentum excluding the most recent month.",
        ("momentum_12_1",),
        "Available at the security month-end.",
    ),
    FactorDefinition(
        "volatility_21d",
        "21-day volatility",
        "Risk",
        "Realized daily-return volatility over the trailing 21 trading days.",
        ("volatility_21d",),
        "Available at the security month-end.",
    ),
    FactorDefinition(
        "liquidity_21d",
        "21-day liquidity",
        "Liquidity",
        "Trailing 21-trading-day liquidity measure from the research source.",
        ("liquidity_21d",),
        "Available at the security month-end.",
    ),
    FactorDefinition(
        "asset_growth",
        "Asset growth",
        "Fundamentals",
        "Growth in reported total assets.",
        ("asset_growth", "fund_available_date"),
        "Usable only after the associated fundamental availability date.",
    ),
    FactorDefinition(
        "leverage",
        "Leverage",
        "Fundamentals",
        "Reported balance-sheet leverage.",
        ("leverage", "fund_available_date"),
        "Usable only after the associated fundamental availability date.",
    ),
    FactorDefinition(
        "profit_margin",
        "Profit margin",
        "Quality",
        "Reported net-income profitability relative to revenue.",
        ("profit_margin", "fund_available_date"),
        "Usable only after the associated fundamental availability date.",
    ),
    FactorDefinition(
        "roe",
        "Return on equity",
        "Quality",
        "Reported net income relative to common equity.",
        ("roe", "fund_available_date"),
        "Usable only after the associated fundamental availability date.",
    ),
    FactorDefinition(
        "ev_ebitda",
        "EV / EBITDA",
        "Valuation",
        "Enterprise value relative to reported EBITDA.",
        ("ev_ebitda", "fund_available_date"),
        "Usable only after the associated fundamental availability date.",
    ),
    FactorDefinition(
        "size",
        "Size",
        "Market",
        "Natural logarithm of positive market capitalization.",
        ("market_cap",),
        "Available at the security month-end.",
    ),
    FactorDefinition(
        "book_to_market",
        "Book-to-market",
        "Valuation",
        "Common equity divided by positive market capitalization.",
        ("ceq", "market_cap", "fund_available_date"),
        "Book equity is usable only after its fundamental availability date.",
    ),
    FactorDefinition(
        "return_1m",
        "One-month return",
        "Momentum",
        "The current calendar month's compounded stock return.",
        ("ret_m",),
        "Available after the security month closes.",
    ),
    FactorDefinition(
        "momentum_6_1",
        "6-1 momentum",
        "Momentum",
        "Compounded returns from calendar months t-6 through t-2.",
        ("log_ret_m",),
        "Requires at least four of the five exact lagged calendar months.",
    ),
    FactorDefinition(
        "turnover",
        "Turnover",
        "Liquidity",
        "The source liquidity measure divided by positive market capitalization.",
        ("liquidity_21d", "market_cap"),
        "Available at the security month-end.",
    ),
    FactorDefinition(
        "relative_volatility",
        "Relative volatility",
        "Risk",
        "Stock 21-day volatility minus the monthly cross-sectional mean.",
        ("volatility_21d",),
        "Available after the month-end cross-section is assembled.",
    ),
)
FACTOR_REGISTRY = {
    definition.factor_id: definition for definition in FACTOR_DEFINITIONS
}
FACTOR_IDS = tuple(FACTOR_REGISTRY)
BASE_FACTOR_IDS = tuple(
    factor_id
    for factor_id in FACTOR_IDS
    if factor_id
    in {
        "momentum_12_1",
        "volatility_21d",
        "liquidity_21d",
        "asset_growth",
        "leverage",
        "profit_margin",
        "roe",
        "ev_ebitda",
    }
)
FUNDAMENTAL_FACTOR_IDS = {
    "asset_growth",
    "leverage",
    "profit_margin",
    "roe",
    "ev_ebitda",
    "book_to_market",
}


def validate_factor_selection(selected_factors: Iterable[str]) -> tuple[str, ...]:
    selected = tuple(selected_factors)
    if not selected:
        raise ValueError("Select at least one factor.")
    if len(set(selected)) != len(selected):
        raise ValueError("Selected factors must not contain duplicates.")
    unknown = sorted(set(selected) - set(FACTOR_IDS))
    if unknown:
        raise ValueError(f"Unknown factors: {', '.join(unknown)}")
    return selected


def factor_catalog() -> pd.DataFrame:
    return pd.DataFrame([definition.to_dict() for definition in FACTOR_DEFINITIONS])


def ranked_factor_column(factor_id: str) -> str:
    validate_factor_selection([factor_id])
    return f"{factor_id}{RANK_SUFFIX}"


def _require_columns(frame: pd.DataFrame, required: Iterable[str]) -> None:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"monthly panel is missing columns: {', '.join(missing)}")


def _calendar_lag(
    panel: pd.DataFrame,
    value_column: str,
    lag_months: int,
) -> pd.Series:
    if lag_months < 1:
        raise ValueError("lag_months must be positive")
    source = panel[[SECURITY_COLUMN, MONTH_COLUMN, value_column]].copy()
    source[MONTH_COLUMN] = source[MONTH_COLUMN] + MonthEnd(lag_months)
    source = source.rename(columns={value_column: "_lagged_value"})
    target = panel[[SECURITY_COLUMN, MONTH_COLUMN]].merge(
        source,
        on=[SECURITY_COLUMN, MONTH_COLUMN],
        how="left",
        validate="one_to_one",
    )
    return target["_lagged_value"].set_axis(panel.index)


def build_factor_panel(monthly_panel: pd.DataFrame) -> pd.DataFrame:
    """Add all registered factors without allowing lags to cross missing months."""
    source_columns = {
        SECURITY_COLUMN,
        MONTH_COLUMN,
        "ret_m",
        "market_cap",
        "ceq",
        "fund_available_date",
        *BASE_FACTOR_IDS,
    }
    _require_columns(monthly_panel, source_columns)
    panel = monthly_panel.copy()
    panel[MONTH_COLUMN] = (
        pd.to_datetime(panel[MONTH_COLUMN], errors="raise")
        .dt.to_period("M")
        .dt.to_timestamp("M")
    )
    if panel.duplicated([SECURITY_COLUMN, MONTH_COLUMN]).any():
        raise ValueError("monthly panel contains duplicate security-month rows")
    panel = panel.sort_values([SECURITY_COLUMN, MONTH_COLUMN]).reset_index(drop=True)

    market_cap = pd.to_numeric(panel["market_cap"], errors="coerce")
    positive_market_cap = market_cap.where(market_cap > 0)
    panel["size"] = np.log(positive_market_cap)
    panel["book_to_market"] = (
        pd.to_numeric(panel["ceq"], errors="coerce") / positive_market_cap
    ).replace([np.inf, -np.inf], np.nan)
    panel["return_1m"] = pd.to_numeric(panel["ret_m"], errors="coerce")

    if "log_ret_m" not in panel:
        panel["log_ret_m"] = np.log1p(panel["return_1m"].clip(lower=-0.99))
    lagged_logs = [
        _calendar_lag(panel, "log_ret_m", lag_months)
        for lag_months in range(2, 7)
    ]
    lagged_frame = pd.concat(lagged_logs, axis=1)
    panel["momentum_6_1"] = np.expm1(
        lagged_frame.sum(axis=1, min_count=4)
    )

    panel["turnover"] = (
        pd.to_numeric(panel["liquidity_21d"], errors="coerce")
        / positive_market_cap
    ).replace([np.inf, -np.inf], np.nan)
    monthly_mean_volatility = panel.groupby(MONTH_COLUMN)[
        "volatility_21d"
    ].transform("mean")
    panel["relative_volatility"] = (
        pd.to_numeric(panel["volatility_21d"], errors="coerce")
        - monthly_mean_volatility
    )

    availability = pd.to_datetime(panel["fund_available_date"], errors="coerce")
    fundamental_is_available = availability.notna() & (
        availability <= panel[MONTH_COLUMN]
    )
    for factor_id in FUNDAMENTAL_FACTOR_IDS:
        panel.loc[~fundamental_is_available, factor_id] = np.nan

    factor_values = panel[list(FACTOR_IDS)].replace([np.inf, -np.inf], np.nan)
    panel[list(FACTOR_IDS)] = factor_values
    panel["available_factor_count"] = factor_values.notna().sum(axis=1)
    panel["factor_completeness"] = (
        panel["available_factor_count"] / len(FACTOR_IDS)
    )
    ranked_values = panel.groupby(MONTH_COLUMN)[list(FACTOR_IDS)].rank(
        method="average",
        pct=True,
    )
    ranked_values = (2.0 * ranked_values - 1.0).fillna(0.0)
    for factor_id in FACTOR_IDS:
        panel[ranked_factor_column(factor_id)] = ranked_values[factor_id]
    panel["feature_version"] = FEATURE_VERSION
    return panel


def rank_normalize_factors(
    factor_panel: pd.DataFrame,
    selected_factors: Iterable[str],
) -> pd.DataFrame:
    """Rank selected factors within each month to [-1, 1], imputing missing at 0."""
    selected = validate_factor_selection(selected_factors)
    _require_columns(factor_panel, {MONTH_COLUMN, *selected})
    ranked = factor_panel.copy()
    ranked_values = ranked.groupby(MONTH_COLUMN)[list(selected)].rank(
        method="average",
        pct=True,
    )
    ranked_values = (2.0 * ranked_values - 1.0).fillna(0.0)
    ranked[list(selected)] = ranked_values
    return ranked


def write_factor_panel(
    monthly_path: str | Path,
    output_path: str | Path,
) -> pd.DataFrame:
    monthly = pd.read_parquet(Path(monthly_path).expanduser().resolve())
    factor_panel = build_factor_panel(monthly)
    destination = Path(output_path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    factor_panel.to_parquet(destination, index=False)
    return factor_panel
