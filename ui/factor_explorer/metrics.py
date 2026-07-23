"""Metric catalog and preset definitions for the factor explorer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricSpec:
    name: str
    metric_type: str
    source_phase: int
    notes: str
    parents: frozenset[str] = frozenset()
    weightable: bool = False


STANDALONE_FACTORS = [
    "Revenue",
    "Net Margin",
    "EPS",
    "FCF",
    "NetCash",
    "Shares",
    "Price",
]

PHASE8_FACTORS = STANDALONE_FACTORS[:6]

DERIVED_METRICS = [
    "EV",
    "eff.dCash",
    "C-Return",
    "eff.Shares",
    "eff.NetMargin",
]

ALL_METRICS = [*STANDALONE_FACTORS, *DERIVED_METRICS]

METRIC_CATALOG: dict[str, MetricSpec] = {
    "Revenue": MetricSpec(
        "Revenue", "factor", 8, "Total gross revenue level.", weightable=True
    ),
    "Net Margin": MetricSpec(
        "Net Margin",
        "factor",
        8,
        "Net income divided by revenue.",
        weightable=True,
    ),
    "EPS": MetricSpec(
        "EPS", "factor", 8, "Net income divided by diluted shares.", weightable=True
    ),
    "FCF": MetricSpec(
        "FCF", "factor", 8, "Total free cash flow level.", weightable=True
    ),
    "NetCash": MetricSpec(
        "NetCash",
        "factor",
        8,
        "Cash plus securities minus debt.",
        weightable=True,
    ),
    "Shares": MetricSpec(
        "Shares", "factor", 8, "Average diluted shares.", weightable=True
    ),
    "Price": MetricSpec(
        "Price",
        "factor",
        9,
        "GOOG split-adjusted year-end close, available from 2004 onward.",
        weightable=True,
    ),
    "EV": MetricSpec(
        "EV",
        "derived-level",
        10,
        "Price minus NetCash per share; YoY is computed on the EV level.",
        frozenset({"Price", "NetCash", "Shares"}),
    ),
    "eff.dCash": MetricSpec(
        "eff.dCash",
        "derived-delta",
        10,
        "dEV minus dPrice.",
        frozenset({"Price", "NetCash", "Shares"}),
    ),
    "C-Return": MetricSpec(
        "C-Return",
        "derived-delta",
        10,
        "dFCF minus eff.dCash.",
        frozenset({"FCF", "Price", "NetCash", "Shares"}),
    ),
    "eff.Shares": MetricSpec(
        "eff.Shares",
        "derived-effective",
        11,
        "(Shares_t-1 / Shares_t - 1) times (1 + dRevenue).",
        frozenset({"Shares", "Revenue"}),
    ),
    "eff.NetMargin": MetricSpec(
        "eff.NetMargin",
        "derived-effective",
        11,
        "dNetMargin times (1 + dRevenuePerShare).",
        frozenset({"Net Margin", "Revenue", "Shares"}),
    ),
}

PRESETS: dict[str, list[str]] = {
    "Phase 8 - 6 factors": PHASE8_FACTORS,
    "Phase 9 - 7 factors": STANDALONE_FACTORS,
    "Phase 10 - EV 4 metrics": ["EV", "Price", "eff.dCash", "C-Return"],
    "Phase 11 - effective 2": ["eff.Shares", "eff.NetMargin"],
}

TOOLTIPS = {
    "overall_rank": "Ranked by mean_abs descending.",
    "mean_abs": "Average absolute YoY move - what we rank by.",
    "mean_weight": (
        "Average share of total movement across periods. "
        "Only available for standalone factor selections."
    ),
    "mean": "Average signed YoY move - shows direction bias.",
    "type": "factor, derived-level, derived-delta, or derived-effective.",
    "positive_periods": "Count of YoY periods where pct_change is positive.",
    "negative_periods": "Count of YoY periods where pct_change is negative.",
    "periods": "Count of valid YoY periods used for that metric.",
}


def metric_type(metric: str) -> str:
    return METRIC_CATALOG[metric].metric_type


def is_standalone(metric: str) -> bool:
    return METRIC_CATALOG[metric].weightable


def has_derived_metric(metrics: list[str]) -> bool:
    return any(not is_standalone(metric) for metric in metrics)


def weights_enabled(metrics: list[str]) -> bool:
    return bool(metrics) and all(is_standalone(metric) for metric in metrics)


def normalize_metric_selection(values: list[object]) -> list[str]:
    """Convert persisted picker display labels back to canonical metric names."""
    normalized: list[str] = []
    for value in values:
        text = str(value)
        if text in METRIC_CATALOG:
            metric = text
        else:
            candidate = text.lstrip("●◇⚠ ").split(" — ", maxsplit=1)[0]
            if candidate not in METRIC_CATALOG:
                continue
            metric = candidate
        if metric not in normalized:
            normalized.append(metric)
    return normalized


def picker_option_label(metric: str, selected_metrics: list[str]) -> str:
    """Describe a metric's weighting impact before it is selected."""
    spec = METRIC_CATALOG[metric]
    normalized_selection = normalize_metric_selection(list(selected_metrics))
    selected = set(normalized_selection)

    if spec.weightable:
        overlapping_derived = [
            selected_metric
            for selected_metric in normalized_selection
            if metric in METRIC_CATALOG[selected_metric].parents
        ]
        if overlapping_derived:
            return (
                f"⚠ {metric} — Weight-ready; overlaps "
                f"{', '.join(overlapping_derived)}"
            )
        return f"● {metric} — Weight-ready"

    overlapping_inputs = sorted(spec.parents & selected)
    if overlapping_inputs:
        return (
            f"⚠ {metric} — Rank-only; overlaps "
            f"{', '.join(overlapping_inputs)}"
        )
    return f"◇ {metric} — Rank-only"


def double_count_conflicts(metrics: list[str]) -> list[tuple[str, str]]:
    selected = set(metrics)
    conflicts: list[tuple[str, str]] = []
    for metric in metrics:
        spec = METRIC_CATALOG[metric]
        for parent in sorted(spec.parents):
            if parent in selected:
                conflicts.append((metric, parent))
    return conflicts


def recommended_full_start(metrics: list[str]) -> int:
    phase10_selected = {"EV", "eff.dCash", "C-Return"} & set(metrics)
    return 2004 if phase10_selected else 2001
