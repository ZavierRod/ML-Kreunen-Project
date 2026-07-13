"""Streamlit app for live GOOG factor ranking and weighting exploration."""

from __future__ import annotations

import html
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from . import charts, engine
    from .metrics import (
        ALL_METRICS,
        METRIC_CATALOG,
        PRESETS,
        TOOLTIPS,
        has_derived_metric,
        recommended_full_start,
    )
except ImportError:  # pragma: no cover - Streamlit runs this file directly.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import charts  # type: ignore
    import engine  # type: ignore
    from metrics import (  # type: ignore
        ALL_METRICS,
        METRIC_CATALOG,
        PRESETS,
        TOOLTIPS,
        has_derived_metric,
        recommended_full_start,
    )


st.set_page_config(page_title="GOOG Factor Explorer", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 4rem;}
    .factor-insight-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.75rem;
        margin: 0.75rem 0 1.25rem;
    }
    .factor-insight-card {
        border: 1px solid rgba(49, 51, 63, 0.14);
        border-left: 4px solid var(--accent-color);
        border-radius: 8px;
        padding: 0.8rem 0.9rem;
        background: #ffffff;
        min-height: 112px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }
    .factor-insight-label {
        color: #64748b;
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0;
        margin-bottom: 0.35rem;
    }
    .factor-insight-value {
        color: #111827;
        font-size: 1.35rem;
        font-weight: 760;
        line-height: 1.15;
        word-break: break-word;
    }
    .factor-insight-caption {
        color: #475569;
        font-size: 0.88rem;
        line-height: 1.35;
        margin-top: 0.45rem;
    }
    @media (max-width: 1100px) {
        .factor-insight-grid {grid-template-columns: repeat(2, minmax(0, 1fr));}
    }
    @media (max-width: 640px) {
        .factor-insight-grid {grid-template-columns: 1fr;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def cached_top_movers() -> list[str]:
    return engine.top_standalone_movers(4)


@st.cache_data(show_spinner=False)
def cached_analysis(selected: tuple[str, ...], start_year: int, end_year: int):
    panel, ranking, conflicts, weight_mode = engine.analyze_selection(
        list(selected), start_year, end_year
    )
    detail = engine.detail_table(panel, list(selected))
    validation = engine.validate_against_reference(
        list(selected), ranking, start_year, end_year
    )
    return panel, ranking, conflicts, weight_mode, detail, validation


@st.cache_data(show_spinner=False)
def cached_preset_comparison(
    selected: tuple[str, ...], start_year: int, end_year: int
) -> pd.DataFrame:
    rows = []
    seen: set[tuple[str, ...]] = set()
    comparison_sets = [("Current selection", list(selected)), *PRESETS.items()]
    for label, metrics in comparison_sets:
        metric_key = tuple(metrics)
        if not metrics or metric_key in seen:
            continue
        seen.add(metric_key)
        panel, ranking, conflicts, weight_mode = engine.analyze_selection(
            list(metrics), start_year, end_year
        )
        valid_ranking = ranking.dropna(subset=["mean_abs"])
        top = valid_ranking.iloc[0] if not valid_ranking.empty else None
        rows.append(
            {
                "preset": label,
                "factor_count": len(metrics),
                "mode": "weighted" if weight_mode else "rank-only",
                "top_metric": "" if top is None else str(top["metric"]),
                "top_mean_abs": pd.NA if top is None else float(top["mean_abs"]),
                "valid_periods": int(panel["period"].nunique()) if not panel.empty else 0,
                "conflicts": ", ".join(f"{a}+{b}" for a, b in conflicts),
            }
        )
    return pd.DataFrame(rows)


def apply_preset(label: str, metrics: list[str], window_choice: str | None = None) -> None:
    st.session_state["selected_metrics"] = metrics
    st.session_state["active_preset"] = label
    if window_choice is not None:
        st.session_state["window_choice"] = window_choice


def format_ranking(ranking: pd.DataFrame) -> pd.DataFrame:
    display = ranking.rename(
        columns={
            "overall_rank": "rank",
            "mean_abs": "mean_abs (%)",
            "mean": "mean (%)",
            "mean_weight": "mean_weight (%)",
            "positive_periods": "up periods",
            "negative_periods": "down periods",
            "periods": "period count",
        }
    ).copy()
    for column in ["mean_abs (%)", "mean (%)", "mean_weight (%)"]:
        if column in display:
            display[column] = display[column] * 100
    return display


def render_html_table(table, *, height: int | None = None) -> None:
    if hasattr(table, "to_html"):
        try:
            html = table.to_html(index=False, escape=False)
        except TypeError:
            html = table.to_html()
    else:
        html = str(table)
    max_height = f"max-height: {height}px;" if height else ""
    st.markdown(
        f"""
        <div style="overflow-x:auto; {max_height} overflow-y:auto;">
        {html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_weight_table(panel: pd.DataFrame, selected_metrics: list[str]) -> pd.DataFrame:
    weights = panel.dropna(subset=["weight"]).pivot_table(
        index="period",
        columns="metric",
        values="weight",
        aggfunc="first",
        dropna=False,
    )
    weights = weights.reindex(columns=selected_metrics).reset_index()
    for column in selected_metrics:
        if column in weights:
            weights[column] = weights[column].map(
                lambda value: "" if pd.isna(value) else f"{float(value) * 100:.1f}%"
            )
    return weights


def format_percent_columns(display: pd.DataFrame) -> pd.DataFrame:
    formatted = display.copy()
    for column in ["mean_abs (%)", "mean (%)", "mean_weight (%)"]:
        if column in formatted:
            formatted[column] = formatted[column].map(
                lambda value: "" if pd.isna(value) else f"{float(value):.1f}"
            )
    return formatted


def format_pct(value: object, *, signed: bool = False) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    number = float(value)
    prefix = "+" if signed and number > 0 else ""
    return f"{prefix}{number * 100:.1f}%"


def format_detail_table(detail: pd.DataFrame, selected_metrics: list[str]) -> pd.DataFrame:
    formatted = detail.astype(object).copy()
    pct_columns = [f"{metric} pct" for metric in selected_metrics]
    weight_columns = [f"{metric} weight" for metric in selected_metrics if f"{metric} weight" in detail]
    for index, row in detail.iterrows():
        values = pd.to_numeric(row[pct_columns], errors="coerce").abs()
        dominant = values.idxmax() if values.notna().any() else None
        for column in [*pct_columns, *weight_columns]:
            value = row[column]
            cell = "" if pd.isna(value) else f"{float(value):.1%}"
            if column == dominant:
                cell = f"<mark><strong>{html.escape(cell)}</strong></mark>"
            formatted.at[index, column] = cell
    return formatted


def render_insight_cards(cards: list[dict[str, str]]) -> None:
    card_html = []
    for card in cards:
        card_html.append(
            '<div class="factor-insight-card" '
            f'style="--accent-color:{html.escape(card["accent"])};">'
            f'<div class="factor-insight-label">{html.escape(card["label"])}</div>'
            f'<div class="factor-insight-value">{html.escape(card["value"])}</div>'
            f'<div class="factor-insight-caption">{html.escape(card["caption"])}</div>'
            "</div>"
        )
    st.markdown(
        f"""<div class="factor-insight-grid">{''.join(card_html)}</div>""",
        unsafe_allow_html=True,
    )


def executive_snapshot(
    panel: pd.DataFrame, ranking: pd.DataFrame, weight_mode: bool
) -> tuple[list[dict[str, str]], list[str]]:
    valid_ranking = ranking.dropna(subset=["mean_abs"]).copy()
    valid_periods = panel.dropna(subset=["pct_change"]).copy()
    valid_periods["abs_pct"] = pd.to_numeric(
        valid_periods["pct_change"], errors="coerce"
    ).abs()

    top = valid_ranking.iloc[0] if not valid_ranking.empty else None
    if valid_ranking.empty:
        persistent = None
    else:
        persistent_ranking = valid_ranking[valid_ranking["periods"] > 0].copy()
        persistent_ranking["positive_rate"] = (
            persistent_ranking["positive_periods"] / persistent_ranking["periods"]
        )
        persistent = persistent_ranking.sort_values(
            ["positive_rate", "mean_abs"], ascending=[False, False]
        ).iloc[0]

    if valid_periods.empty:
        largest = None
        latest = None
    else:
        largest = valid_periods.loc[valid_periods["abs_pct"].idxmax()]
        latest_to_year = valid_periods["to_year"].max()
        latest_period_rows = valid_periods[valid_periods["to_year"] == latest_to_year]
        latest = latest_period_rows.loc[latest_period_rows["abs_pct"].idxmax()]

    cards = [
        {
            "label": "Leading driver",
            "value": "n/a" if top is None else str(top["metric"]),
            "caption": (
                "No valid ranking rows."
                if top is None
                else f"{format_pct(top['mean_abs'])} avg absolute YoY move"
            ),
            "accent": "#2563eb",
        },
        {
            "label": "Most persistent",
            "value": "n/a" if persistent is None else str(persistent["metric"]),
            "caption": (
                "No positive-period signal."
                if persistent is None
                else f"{int(persistent['positive_periods'])}/{int(persistent['periods'])} positive periods"
            ),
            "accent": "#16a34a",
        },
        {
            "label": "Largest swing",
            "value": "n/a" if largest is None else str(largest["metric"]),
            "caption": (
                "No period-level values."
                if largest is None
                else f"{format_pct(largest['pct_change'], signed=True)} in {largest['period']}"
            ),
            "accent": "#d97706",
        },
        {
            "label": "Latest driver",
            "value": "n/a" if latest is None else str(latest["metric"]),
            "caption": (
                "No latest period values."
                if latest is None
                else (
                    f"{format_pct(latest['pct_change'], signed=True)} in {latest['period']}"
                    + (
                        f", {format_pct(latest['weight'])} weight"
                        if weight_mode and not pd.isna(latest.get("weight"))
                        else ""
                    )
                )
            ),
            "accent": "#7c3aed",
        },
    ]

    brief = []
    if top is not None:
        brief.append(
            f"- {top['metric']} leads the selected set with a {format_pct(top['mean_abs'])} average absolute YoY move."
        )
    if persistent is not None:
        brief.append(
            f"- {persistent['metric']} is the cleanest directional story, positive in {int(persistent['positive_periods'])} of {int(persistent['periods'])} valid periods."
        )
    if largest is not None:
        brief.append(
            f"- The biggest single-period move is {largest['metric']} at {format_pct(largest['pct_change'], signed=True)} in {largest['period']}."
        )
    if latest is not None:
        brief.append(
            f"- The latest period is led by {latest['metric']} at {format_pct(latest['pct_change'], signed=True)} in {latest['period']}."
        )
    if weight_mode:
        brief.append("- Weights are live recomputes, so changing the selected standalone factors changes both ranks and weights.")
    else:
        brief.append("- This selection is rank-only because derived metrics are not weighted against their own inputs.")
    return cards, brief


def format_period_table(period_rows: pd.DataFrame, selected_metrics: list[str]) -> pd.DataFrame:
    display = period_rows.copy()
    order = {metric: index for index, metric in enumerate(selected_metrics)}
    display["metric_order"] = display["metric"].map(order)
    display["abs_pct"] = pd.to_numeric(display["pct_change"], errors="coerce").abs()
    display = display.sort_values(["abs_pct", "metric_order"], ascending=[False, True])
    display["pct_change"] = display["pct_change"].map(lambda value: format_pct(value, signed=True))
    if "weight" in display:
        display["weight"] = display["weight"].map(format_pct)
    columns = ["metric", "type", "pct_change"]
    if "weight" in display and display["weight"].ne("n/a").any():
        columns.append("weight")
    return display[columns].rename(columns={"pct_change": "YoY move"})


def format_comparison_table(comparison: pd.DataFrame) -> pd.DataFrame:
    display = comparison.copy()
    display["top_mean_abs"] = display["top_mean_abs"].map(format_pct)
    return display.rename(
        columns={
            "preset": "preset",
            "factor_count": "factors",
            "top_metric": "top metric",
            "top_mean_abs": "top mean abs",
            "valid_periods": "periods",
        }
    )


if "selected_metrics" not in st.session_state:
    st.session_state["selected_metrics"] = PRESETS["Phase 9 - 7 factors"]
if "active_preset" not in st.session_state:
    st.session_state["active_preset"] = "Phase 9 - 7 factors"
if "window_choice" not in st.session_state:
    st.session_state["window_choice"] = "Full history"

st.title("GOOG Factor Explorer")
st.caption(
    "Weights are recomputed for your current standalone-factor selection. "
    "Changing from 4 to 6 factors changes both ranks and weights."
)

with st.sidebar:
    st.header("Factor Picker")

    preset_columns = st.columns(2)
    with preset_columns[0]:
        if st.button("Phase 8 - 6 factors", width="stretch"):
            apply_preset("Phase 8 - 6 factors", PRESETS["Phase 8 - 6 factors"], "Full history")
        if st.button("Phase 10 - EV 4 metrics", width="stretch"):
            apply_preset(
                "Phase 10 - EV 4 metrics",
                PRESETS["Phase 10 - EV 4 metrics"],
                "Full history",
            )
        if st.button("Top 4 movers", width="stretch"):
            apply_preset("Top 4 movers (full history)", cached_top_movers(), "Full history")
    with preset_columns[1]:
        if st.button("Phase 9 - 7 factors", width="stretch"):
            apply_preset("Phase 9 - 7 factors", PRESETS["Phase 9 - 7 factors"], "Full history")
        if st.button("Phase 11 - effective 2", width="stretch"):
            apply_preset(
                "Phase 11 - effective 2",
                PRESETS["Phase 11 - effective 2"],
                "Full history",
            )

    selected_metrics = st.multiselect(
        "Metrics",
        options=ALL_METRICS,
        key="selected_metrics",
        help="Standalone factors can be weighted. Derived metrics are rank-only.",
    )

    st.markdown(f"**{len(selected_metrics)} factors selected**")

    if selected_metrics:
        st.markdown("**Selected metric types**")
        for metric in selected_metrics:
            spec = METRIC_CATALOG[metric]
            st.caption(f"{metric}: {spec.metric_type}, Phase {spec.source_phase}")

    st.header("Window")
    window_choice = st.radio(
        "Date window",
        ["Full history", "Recent 5", "Custom"],
        key="window_choice",
        help="Full history uses 2001-2025, except Phase 10 derived metrics align to 2004-2025.",
    )

    if window_choice == "Full history":
        start_year = recommended_full_start(selected_metrics)
        end_year = 2025
    elif window_choice == "Recent 5":
        start_year = 2020
        end_year = 2025
    else:
        bounds = st.slider(
            "Custom year range",
            min_value=2001,
            max_value=2025,
            value=(2015, 2020),
            step=1,
            help="Rows use YoY periods where from_year >= start and to_year <= end.",
        )
        start_year, end_year = bounds

    st.caption(f"Current period basis: {start_year}-{end_year}")

if not selected_metrics:
    st.info("Select at least one metric to compute rankings.")
    st.stop()

panel, ranking, conflicts, weight_mode, detail, validation = cached_analysis(
    tuple(selected_metrics), start_year, end_year
)

if conflicts:
    conflict_text = ", ".join(f"{derived} + {parent}" for derived, parent in conflicts)
    st.warning(
        "Weights disabled - selection mixes derived metrics with their inputs. "
        f"Conflicts: {conflict_text}."
    )
elif has_derived_metric(selected_metrics):
    st.info("Derived metrics are rank-only; weights are shown only for standalone factor selections.")

summary_cols = st.columns(4)
summary_cols[0].metric("Selected", len(selected_metrics))
summary_cols[1].metric("Window", f"{start_year}-{end_year}")
summary_cols[2].metric("Mode", "Weighted" if weight_mode else "Rank-only")
summary_cols[3].metric("Valid periods", int(panel["period"].nunique()) if not panel.empty else 0)

cards, brief = executive_snapshot(panel, ranking, weight_mode)
st.subheader("Executive Snapshot")
render_insight_cards(cards)

with st.expander("Team brief", expanded=True):
    st.markdown("\n".join(brief))
    st.download_button(
        "Export team brief",
        data=(
            f"# GOOG Factor Brief ({start_year}-{end_year})\n\n"
            + "\n".join(brief)
            + "\n"
        ).encode("utf-8"),
        file_name=f"goog_factor_brief_{start_year}_{end_year}.md",
        mime="text/markdown",
    )

ranking_display = format_ranking(ranking)

st.subheader("Ranking Table")
st.caption("mean_abs: " + TOOLTIPS["mean_abs"])
render_html_table(format_percent_columns(ranking_display))
st.download_button(
    "Export ranking CSV",
    data=ranking_display.to_csv(index=False).encode("utf-8"),
    file_name=f"goog_factor_ranking_{start_year}_{end_year}.csv",
    mime="text/csv",
)

st.subheader("Visual Analysis")
ranking_tab, weight_tab, heatmap_tab, benchmark_tab = st.tabs(
    ["Ranking", "Weights", "Heatmap", "Preset benchmark"]
)
with ranking_tab:
    st.plotly_chart(
        charts.mean_abs_bar(ranking),
        use_container_width=True,
        config={"displayModeBar": False},
    )
with weight_tab:
    weight_fig = charts.weight_area(panel, selected_metrics)
    if weight_fig is not None:
        st.plotly_chart(
            weight_fig,
            use_container_width=True,
            config={"displayModeBar": False},
        )
        render_html_table(format_weight_table(panel, selected_metrics), height=280)
    else:
        st.info("Weights are hidden for rank-only selections.")
with heatmap_tab:
    heatmap_fig = charts.pct_heatmap(panel, selected_metrics)
    if heatmap_fig is not None:
        st.plotly_chart(
            heatmap_fig,
            use_container_width=True,
            config={"displayModeBar": False},
        )
    else:
        st.info("No heatmap values for this selection.")
with benchmark_tab:
    comparison = cached_preset_comparison(tuple(selected_metrics), start_year, end_year)
    benchmark_fig = charts.preset_comparison_bar(comparison)
    if benchmark_fig is not None:
        st.plotly_chart(
            benchmark_fig,
            use_container_width=True,
            config={"displayModeBar": False},
        )
    render_html_table(format_comparison_table(comparison), height=320)

st.subheader("Period Drilldown")
period_options = panel["period"].dropna().drop_duplicates().tolist()
if period_options:
    selected_period = st.select_slider(
        "YoY period",
        options=period_options,
        value=period_options[-1],
        help="Review which factor dominated a single year-over-year period.",
    )
    drill_left, drill_right = st.columns([1.15, 0.85])
    with drill_left:
        st.plotly_chart(
            charts.period_driver_bar(panel, selected_period, selected_metrics),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with drill_right:
        period_rows = panel[panel["period"] == selected_period].copy()
        render_html_table(format_period_table(period_rows, selected_metrics), height=380)
else:
    st.info("No period rows are available for the selected window.")

st.subheader("Per-Period Detail")
detail_row_count = len(detail)
detail_column_count = len(detail.columns)
st.caption(
    f"{detail_row_count} periods x {detail_column_count} columns. "
    "The full grid is hidden by default to keep the app responsive."
)
st.download_button(
    "Export per-period detail CSV",
    data=detail.to_csv(index=False).encode("utf-8"),
    file_name=f"goog_factor_detail_{start_year}_{end_year}.csv",
    mime="text/csv",
)

detail_preview = st.checkbox("Show compact detail preview", value=False)
if detail_preview:
    preview_rows = st.slider(
        "Preview rows",
        min_value=1,
        max_value=max(1, detail_row_count),
        value=min(8, max(1, detail_row_count)),
        step=1,
    )
    st.caption("The highlighted pct_change cell is the dominant mover in that period.")
    render_html_table(format_detail_table(detail.head(preview_rows), selected_metrics), height=420)

full_detail = st.checkbox("Render full detail table", value=False)
if full_detail:
    st.warning("Rendering the full grid can slow the browser on larger selections.")
    st.caption("The highlighted pct_change cell is the dominant mover in that period.")
    render_html_table(format_detail_table(detail, selected_metrics), height=520)

with st.expander("Validation checks", expanded=False):
    validation_df = pd.DataFrame(validation)
    render_html_table(validation_df)
    failing = validation_df[validation_df["status"] == "FAIL"]
    passing = validation_df[validation_df["status"] == "PASS"]
    if not failing.empty:
        st.error(f"{len(failing)} validation check(s) failed.")
    elif not passing.empty:
        st.success("Live recompute matches the phase 8/9 reference CSVs.")
    else:
        st.info("Pick the Phase 8 or Phase 9 full-history preset to run reference checks.")
