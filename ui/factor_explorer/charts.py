"""Plotly chart helpers for the factor explorer."""

from __future__ import annotations

import pandas as pd
import plotly.express as px

try:
    from .metrics import weights_enabled
except ImportError:  # pragma: no cover
    from metrics import weights_enabled  # type: ignore


def mean_abs_bar(ranking: pd.DataFrame):
    data = ranking.sort_values("mean_abs", ascending=True).copy()
    data["mean_abs_pct"] = pd.to_numeric(data["mean_abs"], errors="coerce") * 100
    fig = px.bar(
        data,
        x="mean_abs_pct",
        y="metric",
        color="type",
        orientation="h",
        text=data["mean_abs_pct"].map(lambda value: f"{value:.1f}%"),
        color_discrete_sequence=["#2563eb", "#16a34a", "#d97706", "#7c3aed"],
        labels={"mean_abs_pct": "Mean absolute YoY move (%)", "metric": "Metric"},
        title="Mean Absolute Move Ranking",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=max(360, 42 * len(data)), margin=dict(l=20, r=40, t=50, b=20))
    return fig


def weight_area(panel: pd.DataFrame, selected_metrics: list[str]):
    if not weights_enabled(selected_metrics):
        return None
    data = panel.dropna(subset=["weight"]).copy()
    if data.empty:
        return None
    data["weight_pct"] = data["weight"].astype(float) * 100
    fig = px.area(
        data,
        x="period",
        y="weight_pct",
        color="metric",
        category_orders={"metric": selected_metrics},
        color_discrete_sequence=[
            "#2563eb",
            "#16a34a",
            "#d97706",
            "#7c3aed",
            "#0891b2",
            "#db2777",
            "#475569",
        ],
        labels={"weight_pct": "Weight (%)", "period": "YoY period"},
        title="Period Weights",
    )
    fig.update_layout(yaxis_ticksuffix="%", hovermode="x unified", margin=dict(l=20, r=20, t=50, b=20))
    return fig


def pct_heatmap(panel: pd.DataFrame, selected_metrics: list[str]):
    heatmap = panel.copy()
    if heatmap.empty:
        return None
    heatmap["abs_pct"] = pd.to_numeric(heatmap["pct_change"], errors="coerce").abs() * 100
    matrix = heatmap.pivot(index="metric", columns="period", values="abs_pct")
    matrix = matrix.reindex(index=selected_metrics)
    fig = px.imshow(
        matrix,
        aspect="auto",
        color_continuous_scale="Viridis",
        labels=dict(x="YoY period", y="Metric", color="|pct| (%)"),
        title="Absolute YoY Move Heatmap",
    )
    fig.update_layout(height=max(320, 34 * len(selected_metrics)), margin=dict(l=20, r=20, t=50, b=20))
    return fig


def period_driver_bar(
    panel: pd.DataFrame, selected_period: str, selected_metrics: list[str]
):
    data = panel[panel["period"] == selected_period].copy()
    if data.empty:
        return None
    data["pct_change_pct"] = pd.to_numeric(data["pct_change"], errors="coerce") * 100
    data["abs_pct"] = data["pct_change_pct"].abs()
    metric_order = {metric: index for index, metric in enumerate(selected_metrics)}
    data["metric_order"] = data["metric"].map(metric_order)
    data = data.sort_values(["abs_pct", "metric_order"], ascending=[True, True])
    fig = px.bar(
        data,
        x="pct_change_pct",
        y="metric",
        color="pct_change_pct",
        orientation="h",
        text=data["pct_change_pct"].map(
            lambda value: "" if pd.isna(value) else f"{value:+.1f}%"
        ),
        color_continuous_scale=["#dc2626", "#f8fafc", "#16a34a"],
        labels={"pct_change_pct": "YoY move (%)", "metric": "Metric"},
        title=f"Drivers in {selected_period}",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        height=max(340, 42 * len(data)),
        margin=dict(l=20, r=50, t=50, b=20),
        coloraxis_showscale=False,
        xaxis_ticksuffix="%",
        xaxis_zeroline=True,
        xaxis_zerolinewidth=2,
        xaxis_zerolinecolor="#334155",
    )
    return fig


def preset_comparison_bar(comparison: pd.DataFrame):
    if comparison.empty:
        return None
    data = comparison.copy()
    data["top_mean_abs_pct"] = pd.to_numeric(data["top_mean_abs"], errors="coerce") * 100
    data = data.dropna(subset=["top_mean_abs_pct"])
    if data.empty:
        return None
    fig = px.bar(
        data.sort_values("top_mean_abs_pct", ascending=True),
        x="top_mean_abs_pct",
        y="preset",
        color="mode",
        orientation="h",
        text=data.sort_values("top_mean_abs_pct", ascending=True)[
            "top_mean_abs_pct"
        ].map(lambda value: f"{value:.1f}%"),
        color_discrete_map={"weighted": "#2563eb", "rank-only": "#d97706"},
        labels={"top_mean_abs_pct": "Top metric mean absolute move (%)", "preset": "Preset"},
        title="Top Driver Strength by Preset",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(height=max(320, 44 * len(data)), margin=dict(l=20, r=60, t=50, b=20))
    return fig
