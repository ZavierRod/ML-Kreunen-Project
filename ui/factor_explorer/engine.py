"""Live recomputation engine for the GOOG Factor Explorer."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

import pandas as pd

try:
    from .metrics import (
        ALL_METRICS,
        METRIC_CATALOG,
        PHASE8_FACTORS,
        STANDALONE_FACTORS,
        double_count_conflicts,
        metric_type,
        weights_enabled,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from metrics import (  # type: ignore
        ALL_METRICS,
        METRIC_CATALOG,
        PHASE8_FACTORS,
        STANDALONE_FACTORS,
        double_count_conflicts,
        metric_type,
        weights_enabled,
    )


ROOT = Path(__file__).resolve().parents[2]
PHASE9_LEVELS_PATH = ROOT / "outputs" / "phase9" / "phase9_factor_levels.csv"
PHASE8_REFERENCE_PATH = (
    ROOT / "outputs" / "phase8" / "phase8_six_factor_ranking_full_2001_2025.csv"
)
PHASE9_REFERENCE_PATH = (
    ROOT / "outputs" / "phase9" / "phase9_seven_factor_ranking_full_2001_2025.csv"
)


def _as_optional_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def simple_pct_change(prev: object, cur: object) -> float | None:
    prev_value = _as_optional_float(prev)
    cur_value = _as_optional_float(cur)
    if prev_value is None or cur_value is None or prev_value == 0:
        return None
    return cur_value / prev_value - 1


def subtract(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return a - b


def load_standalone_levels() -> pd.DataFrame:
    """Load the Phase 9 level table used by phases 9-11."""
    if not PHASE9_LEVELS_PATH.exists():
        raise FileNotFoundError(f"Missing {PHASE9_LEVELS_PATH.relative_to(ROOT)}")
    levels = pd.read_csv(PHASE9_LEVELS_PATH)
    levels["year"] = levels["year"].astype(int)
    for column in STANDALONE_FACTORS:
        levels[column] = pd.to_numeric(levels[column], errors="coerce")
    return levels.sort_values("year").reset_index(drop=True)


def _level_records(levels: pd.DataFrame) -> dict[int, dict[str, float | None]]:
    records: dict[int, dict[str, float | None]] = {}
    for row in levels.to_dict("records"):
        records[int(row["year"])] = {
            factor: _as_optional_float(row.get(factor))
            for factor in STANDALONE_FACTORS
        }
    return records


def _net_cash_per_share(level: dict[str, float | None]) -> float | None:
    net_cash = level["NetCash"]
    shares = level["Shares"]
    if net_cash is None or shares is None or shares == 0:
        return None
    return net_cash / shares


def _enterprise_value_per_share(level: dict[str, float | None]) -> float | None:
    price = level["Price"]
    net_cash_per_share = _net_cash_per_share(level)
    if price is None or net_cash_per_share is None:
        return None
    return price - net_cash_per_share


def _rev_per_share(level: dict[str, float | None]) -> float | None:
    revenue = level["Revenue"]
    shares = level["Shares"]
    if revenue is None or shares is None or shares == 0:
        return None
    return revenue / shares


def _shares_base_change(
    prev_shares: float | None, cur_shares: float | None
) -> float | None:
    if prev_shares is None or cur_shares is None or cur_shares == 0:
        return None
    return prev_shares / cur_shares - 1


def _effective_change(
    base_change: float | None, driver_change: float | None
) -> float | None:
    if base_change is None or driver_change is None:
        return None
    return base_change * (1 + driver_change)


def _period_rows(level_records: dict[int, dict[str, float | None]]) -> list[dict]:
    rows: list[dict] = []
    years = sorted(level_records)
    for index in range(1, len(years)):
        prev_year = years[index - 1]
        cur_year = years[index]
        prev = level_records[prev_year]
        cur = level_records[cur_year]

        row = {
            "from_year": prev_year,
            "to_year": cur_year,
            "period": f"{prev_year}-{cur_year}",
        }

        for factor in STANDALONE_FACTORS:
            row[factor] = simple_pct_change(prev[factor], cur[factor])

        price_chg = row["Price"]
        ev_chg = simple_pct_change(
            _enterprise_value_per_share(prev), _enterprise_value_per_share(cur)
        )
        fcf_chg = row["FCF"]
        eff_delta_cash = subtract(ev_chg, price_chg)

        revenue_chg = row["Revenue"]
        margin_chg = row["Net Margin"]
        rev_per_share_chg = simple_pct_change(_rev_per_share(prev), _rev_per_share(cur))
        shares_base = _shares_base_change(prev["Shares"], cur["Shares"])

        row["EV"] = ev_chg
        row["eff.dCash"] = eff_delta_cash
        row["C-Return"] = subtract(fcf_chg, eff_delta_cash)
        row["eff.Shares"] = _effective_change(shares_base, revenue_chg)
        row["eff.NetMargin"] = _effective_change(margin_chg, rev_per_share_chg)
        rows.append(row)
    return rows


def load_derived_panels() -> pd.DataFrame:
    """Build all standalone and derived YoY metric series from level data."""
    levels = load_standalone_levels()
    records = _level_records(levels)
    rows = []
    for period_row in _period_rows(records):
        for metric in ALL_METRICS:
            rows.append(
                {
                    "from_year": period_row["from_year"],
                    "to_year": period_row["to_year"],
                    "period": period_row["period"],
                    "metric": metric,
                    "type": metric_type(metric),
                    "pct_change": period_row[metric],
                }
            )
    return pd.DataFrame(rows)


def compute_panel(
    selected_metrics: list[str], start_year: int, end_year: int
) -> pd.DataFrame:
    """Return long panel rows for selected metrics and period bounds."""
    if not selected_metrics:
        return pd.DataFrame(
            columns=[
                "from_year",
                "to_year",
                "period",
                "metric",
                "type",
                "pct_change",
                "weight",
            ]
        )

    unknown = sorted(set(selected_metrics) - set(ALL_METRICS))
    if unknown:
        raise ValueError(f"Unknown metrics: {', '.join(unknown)}")

    panel = load_derived_panels()
    panel = panel[
        panel["metric"].isin(selected_metrics)
        & (panel["from_year"] >= start_year)
        & (panel["to_year"] <= end_year)
    ].copy()
    panel["weight"] = pd.NA

    if weights_enabled(selected_metrics):
        for _, group in panel.groupby(["from_year", "to_year"], sort=False):
            valid = group.dropna(subset=["pct_change"])
            total = valid["pct_change"].abs().sum()
            if total == 0:
                weights = pd.Series(0.0, index=valid.index)
            else:
                weights = valid["pct_change"].abs() / total
            panel.loc[weights.index, "weight"] = weights

    order = {metric: index for index, metric in enumerate(selected_metrics)}
    panel["metric_order"] = panel["metric"].map(order)
    return panel.sort_values(["from_year", "metric_order"]).reset_index(drop=True)


def compute_rankings(panel: pd.DataFrame, selected_metrics: list[str]) -> pd.DataFrame:
    """Rank metrics by mean absolute YoY move over the current panel."""
    include_weights = weights_enabled(selected_metrics)
    rows = []
    for metric in selected_metrics:
        metric_panel = panel[panel["metric"] == metric]
        values = pd.to_numeric(metric_panel["pct_change"], errors="coerce").dropna()
        weights = pd.to_numeric(metric_panel["weight"], errors="coerce").dropna()

        if values.empty:
            row = {
                "metric": metric,
                "type": metric_type(metric),
                "mean_abs": math.nan,
                "mean": math.nan,
                "positive_periods": 0,
                "negative_periods": 0,
                "periods": 0,
            }
        else:
            row = {
                "metric": metric,
                "type": metric_type(metric),
                "mean_abs": float(values.abs().mean()),
                "mean": float(values.mean()),
                "positive_periods": int((values > 0).sum()),
                "negative_periods": int((values < 0).sum()),
                "periods": int(values.count()),
            }
        if include_weights:
            row["mean_weight"] = float(weights.mean()) if not weights.empty else math.nan
        rows.append(row)

    ranking = pd.DataFrame(rows)
    ranking = ranking.sort_values(
        ["mean_abs", "metric"], ascending=[False, True], na_position="last"
    ).reset_index(drop=True)
    ranking.insert(0, "overall_rank", range(1, len(ranking) + 1))

    ordered = [
        "overall_rank",
        "metric",
        "type",
        "mean_abs",
        "mean",
    ]
    if include_weights:
        ordered.append("mean_weight")
    ordered.extend(["positive_periods", "negative_periods", "periods"])
    return ranking[ordered]


def analyze_selection(
    selected_metrics: list[str], start_year: int, end_year: int
) -> tuple[pd.DataFrame, pd.DataFrame, list[tuple[str, str]], bool]:
    panel = compute_panel(selected_metrics, start_year, end_year)
    ranking = compute_rankings(panel, selected_metrics)
    return (
        panel,
        ranking,
        double_count_conflicts(selected_metrics),
        weights_enabled(selected_metrics),
    )


def detail_table(panel: pd.DataFrame, selected_metrics: list[str]) -> pd.DataFrame:
    # Each panel row is unique by period and metric. ``pivot_table`` with
    # ``dropna=False`` expands a multi-column index into the Cartesian product
    # of all start years, end years, and period labels, creating mostly-empty
    # synthetic rows. A strict pivot preserves only periods present in panel.
    pct_wide = panel.pivot(
        index=["from_year", "to_year", "period"],
        columns="metric",
        values="pct_change",
    )
    pct_wide = pct_wide.reindex(columns=selected_metrics)
    pct_wide.columns = [f"{metric} pct" for metric in pct_wide.columns]

    if weights_enabled(selected_metrics):
        weight_wide = panel.pivot(
            index=["from_year", "to_year", "period"],
            columns="metric",
            values="weight",
        )
        weight_wide = weight_wide.reindex(columns=selected_metrics)
        weight_wide.columns = [f"{metric} weight" for metric in weight_wide.columns]
        wide = pd.concat([pct_wide, weight_wide], axis=1)
    else:
        wide = pct_wide

    return wide.reset_index().sort_values(["from_year", "to_year"])


def top_standalone_movers(count: int = 4) -> list[str]:
    panel = compute_panel(STANDALONE_FACTORS, 2001, 2025)
    ranking = compute_rankings(panel, STANDALONE_FACTORS)
    return ranking.head(count)["metric"].tolist()


def _reference_path_for(metrics: Iterable[str]) -> Path | None:
    metric_set = set(metrics)
    if metric_set == set(PHASE8_FACTORS):
        return PHASE8_REFERENCE_PATH
    if metric_set == set(STANDALONE_FACTORS):
        return PHASE9_REFERENCE_PATH
    return None


def validate_against_reference(
    selected_metrics: list[str],
    ranking: pd.DataFrame,
    start_year: int,
    end_year: int,
    tolerance: float = 1e-6,
) -> list[dict[str, str]]:
    """Validate current live ranking against phase 8/9 full-history CSVs."""
    reference_path = _reference_path_for(selected_metrics)
    if reference_path is None:
        return [
            {
                "check": "reference_match",
                "status": "SKIP",
                "details": "No phase 8/9 full-history reference for this selection.",
            }
        ]
    if start_year != 2001 or end_year != 2025:
        return [
            {
                "check": "reference_match",
                "status": "SKIP",
                "details": "Reference checks apply to full history 2001-2025.",
            }
        ]

    reference = pd.read_csv(reference_path)
    reference = reference.rename(
        columns={
            "factor": "metric",
            "mean_abs_pct_change": "mean_abs",
            "mean_pct_change": "mean",
        }
    )
    current = ranking.copy()

    checks: list[dict[str, str]] = []
    key_columns = [
        "overall_rank",
        "mean_abs",
        "mean",
        "mean_weight",
        "positive_periods",
        "negative_periods",
        "periods",
    ]

    merged = current.merge(reference, on="metric", suffixes=("_live", "_ref"))
    if len(merged) != len(reference):
        missing = sorted(set(reference["metric"]) - set(current["metric"]))
        checks.append(
            {
                "check": "reference_rows",
                "status": "FAIL",
                "details": f"Missing reference metrics: {', '.join(missing)}",
            }
        )
        return checks

    for column in key_columns:
        live_col = f"{column}_live"
        ref_col = f"{column}_ref"
        if live_col not in merged or ref_col not in merged:
            continue
        if column in {"mean_abs", "mean", "mean_weight"}:
            diff = (merged[live_col] - merged[ref_col]).abs().max()
            passed = bool(diff <= tolerance)
            details = f"max abs diff {diff:.2e} vs {reference_path.relative_to(ROOT)}"
        else:
            passed = bool((merged[live_col] == merged[ref_col]).all())
            mismatched = merged.loc[merged[live_col] != merged[ref_col], "metric"].tolist()
            details = (
                "all rows match"
                if passed
                else f"mismatched metrics: {', '.join(mismatched)}"
            )
        checks.append(
            {
                "check": column,
                "status": "PASS" if passed else "FAIL",
                "details": details,
            }
        )

    return checks


def run_phase8_phase9_validations() -> pd.DataFrame:
    rows = []
    for label, metrics in (
        ("Phase 8 - 6 factors", PHASE8_FACTORS),
        ("Phase 9 - 7 factors", STANDALONE_FACTORS),
    ):
        panel = compute_panel(metrics, 2001, 2025)
        ranking = compute_rankings(panel, metrics)
        for check in validate_against_reference(metrics, ranking, 2001, 2025):
            rows.append({"validation": label, **check})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    validation = run_phase8_phase9_validations()
    print(validation.to_string(index=False))
    failures = validation[validation["status"] == "FAIL"]
    raise SystemExit(1 if not failures.empty else 0)
