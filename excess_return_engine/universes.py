"""Versioned point-in-time model-training universe definitions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

UNIVERSE_VERSION = "training-universe-v1"
ALL_COVERED_UNIVERSE_ID = "all-covered"
LARGE_LIQUID_UNIVERSE_ID = "large-liquid-research"


@dataclass(frozen=True)
class TrainingUniverseDefinition:
    universe_id: str
    label: str
    method: str
    limitation: str


@dataclass(frozen=True)
class TrainingUniverseSelection:
    version: str
    universe_id: str
    label: str
    method: str
    limitation: str
    input_rows: int
    retained_rows: int
    retained_share: float
    retained_months: int
    retained_securities: int
    minimum_monthly_constituents: int


UNIVERSE_DEFINITIONS = (
    TrainingUniverseDefinition(
        universe_id=ALL_COVERED_UNIVERSE_ID,
        label="All covered securities",
        method="Retain every eligible labeled security-month in the panel.",
        limitation=(
            "Includes small, low-price, and less frequently traded securities "
            "represented in the research panel."
        ),
    ),
    TrainingUniverseDefinition(
        universe_id=LARGE_LIQUID_UNIVERSE_ID,
        label="Large and liquid research universe",
        method=(
            "For each factor month, require positive market capitalization, "
            "absolute month-end price of at least $5, at least 15 observed "
            "trading days, and market capitalization at or above that month's "
            "eligible median."
        ),
        limitation=(
            "A research investability screen, not membership in an official "
            "index; thresholds are not transaction-cost or capacity estimates."
        ),
    ),
)


def universe_options() -> tuple[TrainingUniverseDefinition, ...]:
    return UNIVERSE_DEFINITIONS


def apply_training_universe(
    historical: pd.DataFrame,
    universe_id: str | None,
) -> tuple[pd.DataFrame, TrainingUniverseSelection]:
    """Filter historical rows using only same-month observable fields."""
    resolved_id = universe_id or ALL_COVERED_UNIVERSE_ID
    definitions = {
        item.universe_id: item for item in UNIVERSE_DEFINITIONS
    }
    if resolved_id not in definitions:
        raise ValueError(f"Unsupported training universe: {resolved_id}.")
    required = {"month_end"}
    if resolved_id == LARGE_LIQUID_UNIVERSE_ID:
        required.update(
            {"permno", "market_cap", "dlyprc", "n_days"}
        )
    missing = sorted(required - set(historical.columns))
    if missing:
        raise ValueError(
            "Training panel is missing universe columns: "
            + ", ".join(missing)
        )

    source = historical.copy()
    if resolved_id == ALL_COVERED_UNIVERSE_ID:
        retained = source
    else:
        market_cap = pd.to_numeric(
            source["market_cap"],
            errors="coerce",
        )
        price = pd.to_numeric(source["dlyprc"], errors="coerce").abs()
        trading_days = pd.to_numeric(
            source["n_days"],
            errors="coerce",
        )
        base_eligible = (
            market_cap.notna()
            & np.isfinite(market_cap)
            & (market_cap > 0)
            & price.notna()
            & np.isfinite(price)
            & (price >= 5)
            & trading_days.notna()
            & np.isfinite(trading_days)
            & (trading_days >= 15)
        )
        eligible_market_cap = market_cap.where(base_eligible)
        market_cap_percentile = eligible_market_cap.groupby(
            source["month_end"],
            sort=False,
        ).rank(method="average", pct=True)
        retained = source[
            base_eligible & (market_cap_percentile >= 0.50)
        ].copy()

    if retained.empty:
        raise ValueError(
            f"Training universe {resolved_id} retained no historical rows."
        )
    if "permno" in retained:
        monthly_counts = retained.groupby("month_end")["permno"].nunique()
        retained_securities = int(retained["permno"].nunique())
    else:
        monthly_counts = retained.groupby("month_end").size()
        retained_securities = 0
    definition = definitions[resolved_id]
    selection = TrainingUniverseSelection(
        version=UNIVERSE_VERSION,
        universe_id=definition.universe_id,
        label=definition.label,
        method=definition.method,
        limitation=definition.limitation,
        input_rows=int(len(source)),
        retained_rows=int(len(retained)),
        retained_share=float(len(retained) / len(source)),
        retained_months=int(retained["month_end"].nunique()),
        retained_securities=retained_securities,
        minimum_monthly_constituents=int(monthly_counts.min()),
    )
    return retained, selection
