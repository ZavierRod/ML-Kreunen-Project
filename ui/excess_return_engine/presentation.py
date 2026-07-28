"""Pure presentation helpers for the excess-return Streamlit app."""

from __future__ import annotations

import pandas as pd

from excess_return_engine.features import FACTOR_REGISTRY
from excess_return_engine.model import ForecastResult

FACTOR_PRESETS = {
    "Balanced": (
        "momentum_12_1",
        "volatility_21d",
        "asset_growth",
        "leverage",
        "profit_margin",
        "roe",
        "ev_ebitda",
        "size",
    ),
    "Momentum": (
        "momentum_12_1",
        "return_1m",
        "momentum_6_1",
        "relative_volatility",
    ),
    "Fundamentals": (
        "asset_growth",
        "leverage",
        "profit_margin",
        "roe",
        "book_to_market",
        "ev_ebitda",
    ),
    "Risk & liquidity": (
        "volatility_21d",
        "relative_volatility",
        "liquidity_21d",
        "turnover",
        "size",
    ),
}


def company_options(inference: pd.DataFrame) -> list[tuple[str, int]]:
    required = {"permno", "ticker", "company"}
    missing = sorted(required - set(inference.columns))
    if missing:
        raise ValueError(f"inference panel is missing columns: {', '.join(missing)}")
    companies = (
        inference[["permno", "ticker", "company"]]
        .drop_duplicates("permno")
        .sort_values(["ticker", "company", "permno"], na_position="last")
    )
    options = []
    for row in companies.itertuples(index=False):
        ticker = str(row.ticker) if pd.notna(row.ticker) else "No ticker"
        company = str(row.company) if pd.notna(row.company) else "Unknown company"
        options.append((f"{ticker} · {company} · PERMNO {int(row.permno)}", int(row.permno)))
    return options


def factor_option_label(factor_id: str) -> str:
    definition = FACTOR_REGISTRY[factor_id]
    return f"{definition.label} · {definition.category}"


def configuration_quality(
    training: pd.DataFrame,
    inference: pd.DataFrame,
    permno: int,
    selected_factors: tuple[str, ...],
) -> dict[str, float | int | str]:
    if not selected_factors:
        return {
            "status": "blocked",
            "message": "Select at least one factor.",
            "training_rows": 0,
            "training_months": 0,
            "current_completeness": 0.0,
            "historical_coverage": 0.0,
        }
    current = inference[inference["permno"] == permno]
    if len(current) != 1:
        return {
            "status": "blocked",
            "message": "The selected security does not have one current inference row.",
            "training_rows": 0,
            "training_months": 0,
            "current_completeness": 0.0,
            "historical_coverage": 0.0,
        }

    relevant = training.dropna(subset=["excess_return_next_month"])
    current_completeness = float(
        current.iloc[0][list(selected_factors)].notna().mean()
    )
    historical_coverage = float(
        relevant[list(selected_factors)].notna().mean().mean()
    )
    training_months = int(relevant["month_end"].nunique())
    status = "ready"
    message = "Configuration passes the research minimums."
    if training_months < 96:
        status = "blocked"
        message = "At least 96 historical months are required."
    elif current_completeness < 0.75:
        status = "blocked"
        message = "Current selected-factor completeness must be at least 75%."
    elif historical_coverage < 0.70:
        status = "blocked"
        message = "Historical selected-factor coverage must be at least 70%."

    return {
        "status": status,
        "message": message,
        "training_rows": int(len(relevant)),
        "training_months": training_months,
        "current_completeness": current_completeness,
        "historical_coverage": historical_coverage,
    }


def contribution_table(result: ForecastResult) -> pd.DataFrame:
    rows = []
    for contribution in result.contributions:
        definition = FACTOR_REGISTRY[contribution.factor_id]
        rows.append(
            {
                "factor_id": contribution.factor_id,
                "factor": definition.label,
                "category": definition.category,
                "normalized_value": contribution.normalized_value,
                "coefficient": contribution.coefficient,
                "contribution": contribution.contribution,
            }
        )
    return pd.DataFrame(rows).sort_values(
        "contribution",
        key=lambda values: values.abs(),
        ascending=False,
    )


def predictive_strength_label(metrics: dict[str, float | int]) -> str:
    r2 = float(metrics["oos_r2_vs_zero"])
    directional = float(metrics["directional_hit_rate"])
    if r2 <= 0 or directional < 0.49:
        return "Weak"
    if r2 < 0.01 or directional < 0.52:
        return "Modest"
    if r2 < 0.03 or directional < 0.55:
        return "Moderate"
    return "Strong"
