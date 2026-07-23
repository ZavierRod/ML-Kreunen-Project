"""Streamlit app for live GOOG factor ranking and weighting exploration."""

from __future__ import annotations

import hashlib
import html
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from . import charts, engine, llm
    from .metrics import (
        ALL_METRICS,
        METRIC_CATALOG,
        PRESETS,
        TOOLTIPS,
        double_count_conflicts,
        has_derived_metric,
        normalize_metric_selection,
        picker_option_label,
        recommended_full_start,
        weights_enabled,
    )
except ImportError:  # pragma: no cover - Streamlit runs this file directly.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import charts  # type: ignore
    import engine  # type: ignore
    import llm  # type: ignore
    from metrics import (  # type: ignore
        ALL_METRICS,
        METRIC_CATALOG,
        PRESETS,
        TOOLTIPS,
        double_count_conflicts,
        has_derived_metric,
        normalize_metric_selection,
        picker_option_label,
        recommended_full_start,
        weights_enabled,
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
    .analyst-answer {
        border: 1px solid rgba(49, 51, 63, 0.14);
        border-radius: 8px;
        padding: 1rem;
        background: #ffffff;
        margin-top: 0.75rem;
    }
    .analyst-point {
        border-left: 3px solid #2563eb;
        padding: 0.55rem 0.75rem;
        margin: 0.5rem 0;
        background: #f8fafc;
    }
    .analyst-point strong {color: #111827;}
    .picker-legend {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin: 0.35rem 0 0.65rem;
    }
    .picker-badge {
        border-radius: 999px;
        padding: 0.18rem 0.55rem;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.01em;
    }
    .picker-badge-weighted {
        color: #166534;
        background: #dcfce7;
        border: 1px solid #86efac;
    }
    .picker-badge-rank {
        color: #92400e;
        background: #fef3c7;
        border: 1px solid #fcd34d;
    }
    .picker-mode {
        border: 1px solid var(--mode-border);
        border-left: 4px solid var(--mode-accent);
        border-radius: 8px;
        padding: 0.65rem 0.75rem;
        background: var(--mode-background);
        margin-top: 0.65rem;
    }
    .picker-mode-title {
        color: #111827;
        font-size: 0.86rem;
        font-weight: 750;
    }
    .picker-mode-copy {
        color: #475569;
        font-size: 0.76rem;
        line-height: 1.35;
        margin-top: 0.2rem;
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


def mark_custom_selection() -> None:
    st.session_state["active_preset"] = "Custom selection"
    stored = list(st.session_state.get("selected_metrics", []))
    st.session_state["selected_metrics"] = normalize_metric_selection(stored)


def render_picker_mode(selected_metrics: list[str]) -> None:
    conflicts = double_count_conflicts(selected_metrics)
    if not selected_metrics:
        title = "Choose at least one metric"
        copy = "The analysis starts as soon as you make a selection."
        colors = ("#94a3b8", "#cbd5e1", "#f8fafc")
    elif weights_enabled(selected_metrics):
        title = "Weighted mode"
        copy = "All selected factors are weight-ready; weights will be recomputed live."
        colors = ("#16a34a", "#86efac", "#f0fdf4")
    elif conflicts:
        title = "Rank-only · overlapping inputs"
        pairs = ", ".join(f"{derived} + {parent}" for derived, parent in conflicts)
        copy = f"Derived metrics disable weights. Review possible double counts: {pairs}."
        colors = ("#dc2626", "#fca5a5", "#fef2f2")
    else:
        title = "Rank-only mode"
        copy = "A derived metric is selected, so weights are disabled for this view."
        colors = ("#d97706", "#fcd34d", "#fffbeb")

    accent, border, background = colors
    st.markdown(
        f"""
        <div class="picker-mode" style="--mode-accent:{accent};--mode-border:{border};--mode-background:{background};">
          <div class="picker-mode-title">{html.escape(title)}</div>
          <div class="picker-mode-copy">{html.escape(copy)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_overview(
    section_key: str,
    section_context: dict[str, object],
    *,
    model: str,
    api_key: str | None,
) -> None:
    scoped_context = llm.context_for_section_overview(section_context, section_key)
    context_json = json.dumps(scoped_context, sort_keys=True, separators=(",", ":"))
    context_id = hashlib.sha256(context_json.encode("utf-8")).hexdigest()
    cache = st.session_state.setdefault("section_overview_results", {})
    record = cache.get(section_key)
    is_current = isinstance(record, dict) and record.get("context_id") == context_id
    overview = record.get("overview") if is_current else None

    with st.expander("AI overview", expanded=False):
        st.caption(f"{model} · generated only when requested")

        if record and not is_current:
            st.info("The analysis controls changed. Generate a new overview when you want it.")

        button_label = "Regenerate overview" if is_current else "Generate overview"
        if st.button(button_label, key=f"generate_{section_key}", type="secondary"):
            if not api_key:
                st.warning("Set `OPENAI_API_KEY` to generate this overview.")
            else:
                try:
                    with st.spinner("Generating this section overview..."):
                        overview = llm.generate_section_overview(
                            section_key=section_key,
                            context=scoped_context,
                            api_key=api_key,
                            model=model,
                        )
                    cache[section_key] = {
                        "context_id": context_id,
                        "overview": overview,
                    }
                    st.session_state["section_overview_results"] = cache
                    is_current = True
                except Exception as exc:
                    st.warning(f"The section overview could not be generated: {exc}")

        if isinstance(overview, dict):
            summary = overview.get("summary")
            if summary:
                st.markdown(str(summary))

            key_points = overview.get("key_points")
            if isinstance(key_points, list) and key_points:
                st.markdown("**What stands out**")
                for point in key_points:
                    st.markdown(f"- {point}")

            how_to_read = overview.get("how_to_read")
            if how_to_read:
                st.markdown(f"**How to read this:** {how_to_read}")

            caveat = overview.get("caveat")
            if caveat:
                st.caption(f"Keep in mind: {caveat}")


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


def render_analyst_answer(answer: dict[str, object]) -> None:
    st.markdown(
        f"""
        <div class="analyst-answer">
          {html.escape(str(answer.get("answer", "")))}
        </div>
        """,
        unsafe_allow_html=True,
    )

    supporting_points = answer.get("supporting_points", [])
    if isinstance(supporting_points, list) and supporting_points:
        st.markdown("**Supporting rows**")
        for point in supporting_points:
            if not isinstance(point, dict):
                continue
            metric = html.escape(str(point.get("metric", "")))
            period = html.escape(str(point.get("period", "")))
            value = html.escape(str(point.get("value", "")))
            explanation = html.escape(str(point.get("explanation", "")))
            st.markdown(
                f"""
                <div class="analyst-point">
                  <strong>{metric}</strong> <span>{period}</span> <code>{value}</code><br>
                  {explanation}
                </div>
                """,
                unsafe_allow_html=True,
            )

    caveats = answer.get("caveats", [])
    if isinstance(caveats, list) and caveats:
        st.markdown("**Caveats**")
        for caveat in caveats:
            st.caption(str(caveat))

    followups = answer.get("suggested_followups", [])
    if isinstance(followups, list) and followups:
        st.markdown("**Suggested follow-ups**")
        for index, followup in enumerate(followups):
            followup_text = str(followup).strip()
            if not followup_text:
                continue
            if st.button(
                followup_text,
                key=f"analyst_followup_{index}",
                width="stretch",
            ):
                st.session_state["analyst_pending_question"] = followup_text
                st.rerun()


def render_ask_data_panel(
    *,
    panel: pd.DataFrame,
    ranking: pd.DataFrame,
    selected_metrics: list[str],
    start_year: int,
    end_year: int,
    conflicts: list[tuple[str, str]],
    weight_mode: bool,
    validation: list[dict[str, str]],
    brief: list[str],
) -> None:
    st.subheader("Ask the Data")
    st.caption(
        "Ask questions about the current factor selection, window, rankings, weights, and period moves."
    )

    pending_question = st.session_state.pop("analyst_pending_question", None)
    auto_submit = isinstance(pending_question, str) and bool(pending_question.strip())
    if auto_submit:
        st.session_state["analyst_question"] = pending_question.strip()

    if "analyst_question" not in st.session_state:
        st.session_state["analyst_question"] = "What is the clearest takeaway from this view?"

    examples = [
        "Why is the top-ranked metric leading this view?",
        "What changed in the latest period?",
        "Which period was the biggest outlier?",
        "Summarize this for a finance team in three bullets.",
    ]
    example_cols = st.columns(4)
    for column, example in zip(example_cols, examples):
        with column:
            if st.button(example, width="stretch"):
                st.session_state["analyst_question"] = example

    question = st.text_area(
        "Question",
        key="analyst_question",
        height=90,
        help="The model only receives the data currently visible in this app state.",
    )

    api_key = llm.api_key_from_environment(st.secrets)
    model = llm.model_from_environment(st.secrets)
    if not api_key:
        st.info(
            "Set `OPENAI_API_KEY` to enable live answers. The app will keep running without it."
        )
    else:
        st.caption(f"Model: `{model}`")

    ask_cols = st.columns([1, 1, 4])
    with ask_cols[0]:
        ask_clicked = st.button(
            "Ask analyst",
            type="primary",
            disabled=not api_key or not question.strip(),
        )
    with ask_cols[1]:
        if st.button("Clear answer"):
            st.session_state.pop("analyst_answer", None)
            st.session_state.pop("analyst_error", None)

    if (ask_clicked or auto_submit) and api_key:
        context = llm.build_analysis_context(
            selected_metrics=selected_metrics,
            start_year=start_year,
            end_year=end_year,
            panel=panel,
            ranking=ranking,
            metric_catalog=METRIC_CATALOG,
            conflicts=conflicts,
            weight_mode=weight_mode,
            validation=validation,
            brief=brief,
        )
        with st.spinner("Analyzing the current factor view..."):
            try:
                st.session_state["analyst_answer"] = llm.answer_question(
                    question=question.strip(),
                    context=context,
                    api_key=api_key,
                    model=model,
                )
                st.session_state.pop("analyst_error", None)
            except Exception as exc:
                st.session_state["analyst_error"] = str(exc)

    if st.session_state.get("analyst_error"):
        st.error(st.session_state["analyst_error"])
    if st.session_state.get("analyst_answer"):
        render_analyst_answer(st.session_state["analyst_answer"])


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
    st.header("Build Your Factor Set")
    st.caption("Start with a preset or assemble a custom comparison.")

    with st.container(border=True):
        st.markdown("**Quick starts**")
        preset_columns = st.columns(2)
        with preset_columns[0]:
            if st.button("Phase 8 · 6", width="stretch", help="Six standalone factors; weighted."):
                apply_preset(
                    "Phase 8 - 6 factors",
                    PRESETS["Phase 8 - 6 factors"],
                    "Full history",
                )
            if st.button("Phase 10 · EV", width="stretch", help="EV-derived comparison; rank-only."):
                apply_preset(
                    "Phase 10 - EV 4 metrics",
                    PRESETS["Phase 10 - EV 4 metrics"],
                    "Full history",
                )
            if st.button("Top 4 movers", width="stretch", help="Largest standalone movers; weighted."):
                apply_preset(
                    "Top 4 movers (full history)",
                    cached_top_movers(),
                    "Full history",
                )
        with preset_columns[1]:
            if st.button("Phase 9 · 7", width="stretch", help="Seven standalone factors; weighted."):
                apply_preset(
                    "Phase 9 - 7 factors",
                    PRESETS["Phase 9 - 7 factors"],
                    "Full history",
                )
            if st.button("Phase 11 · effective", width="stretch", help="Effective derived metrics; rank-only."):
                apply_preset(
                    "Phase 11 - effective 2",
                    PRESETS["Phase 11 - effective 2"],
                    "Full history",
                )
        st.caption(f"Active: {st.session_state['active_preset']}")

    with st.container(border=True):
        st.markdown("**Choose metrics**")
        st.markdown(
            """
            <div class="picker-legend">
              <span class="picker-badge picker-badge-weighted">● Weight-ready</span>
              <span class="picker-badge picker-badge-rank">◇ Rank-only</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Adding any ◇ derived metric switches the entire view to rank-only.")

        stored_selection = list(st.session_state.get("selected_metrics", []))
        current_selection = normalize_metric_selection(stored_selection)
        if current_selection != stored_selection:
            st.session_state["selected_metrics"] = current_selection
        selected_metrics = st.multiselect(
            "Factors and derived metrics",
            options=ALL_METRICS,
            key="selected_metrics",
            format_func=lambda metric: picker_option_label(metric, current_selection),
            placeholder="Add a metric",
            help=(
                "Every option shows its weighting impact before selection. "
                "A warning symbol marks overlap with a currently selected input."
            ),
            on_change=mark_custom_selection,
        )
        selected_metrics = normalize_metric_selection(list(selected_metrics))

        render_picker_mode(selected_metrics)
        st.caption(f"{len(selected_metrics)} selected")

        if selected_metrics:
            with st.expander("Selection details"):
                for metric in selected_metrics:
                    spec = METRIC_CATALOG[metric]
                    mode = "Weight-ready" if spec.weightable else "Rank-only"
                    st.markdown(
                        f"**{metric}**  \n{mode} · {spec.metric_type} · Phase {spec.source_phase}"
                    )

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

comparison = cached_preset_comparison(tuple(selected_metrics), start_year, end_year)
period_options = panel["period"].dropna().drop_duplicates().tolist()
if period_options:
    if st.session_state.get("selected_period") not in period_options:
        st.session_state["selected_period"] = period_options[-1]
    selected_period: str | None = st.session_state["selected_period"]
else:
    selected_period = None

section_api_key = llm.api_key_from_environment(st.secrets)
section_model = llm.model_from_environment(st.secrets)
analysis_context = llm.build_analysis_context(
    selected_metrics=selected_metrics,
    start_year=start_year,
    end_year=end_year,
    panel=panel,
    ranking=ranking,
    metric_catalog=METRIC_CATALOG,
    conflicts=conflicts,
    weight_mode=weight_mode,
    validation=validation,
    brief=brief,
)
section_context = llm.build_section_overview_context(
    analysis_context=analysis_context,
    panel=panel,
    detail=detail,
    preset_comparison=comparison,
    selected_period=selected_period,
)

render_ask_data_panel(
    panel=panel,
    ranking=ranking,
    selected_metrics=selected_metrics,
    start_year=start_year,
    end_year=end_year,
    conflicts=conflicts,
    weight_mode=weight_mode,
    validation=validation,
    brief=brief,
)

ranking_display = format_ranking(ranking)

st.subheader("Ranking Table")
render_section_overview(
    "ranking_table",
    section_context,
    model=section_model,
    api_key=section_api_key,
)
st.caption("mean_abs: " + TOOLTIPS["mean_abs"])
render_html_table(format_percent_columns(ranking_display))
st.download_button(
    "Export ranking CSV",
    data=ranking_display.to_csv(index=False).encode("utf-8"),
    file_name=f"goog_factor_ranking_{start_year}_{end_year}.csv",
    mime="text/csv",
)

st.subheader("Visual Analysis")
render_section_overview(
    "visual_analysis",
    section_context,
    model=section_model,
    api_key=section_api_key,
)
ranking_tab, weight_tab, heatmap_tab, benchmark_tab = st.tabs(
    ["Ranking", "Weights", "Heatmap", "Preset benchmark"]
)
with ranking_tab:
    st.plotly_chart(
        charts.mean_abs_bar(ranking),
        width="stretch",
        config={"displayModeBar": False},
    )
with weight_tab:
    weight_fig = charts.weight_area(panel, selected_metrics)
    if weight_fig is not None:
        st.plotly_chart(
            weight_fig,
            width="stretch",
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
            width="stretch",
            config={"displayModeBar": False},
        )
    else:
        st.info("No heatmap values for this selection.")
with benchmark_tab:
    benchmark_fig = charts.preset_comparison_bar(comparison)
    if benchmark_fig is not None:
        st.plotly_chart(
            benchmark_fig,
            width="stretch",
            config={"displayModeBar": False},
        )
    render_html_table(format_comparison_table(comparison), height=320)

st.subheader("Period Drilldown")
render_section_overview(
    "period_drilldown",
    section_context,
    model=section_model,
    api_key=section_api_key,
)
if period_options:
    selected_period = st.select_slider(
        "YoY period",
        options=period_options,
        key="selected_period",
        help="Review which factor dominated a single year-over-year period.",
    )
    drill_left, drill_right = st.columns([1.15, 0.85])
    with drill_left:
        st.plotly_chart(
            charts.period_driver_bar(panel, selected_period, selected_metrics),
            width="stretch",
            config={"displayModeBar": False},
        )
    with drill_right:
        period_rows = panel[panel["period"] == selected_period].copy()
        render_html_table(format_period_table(period_rows, selected_metrics), height=380)
else:
    st.info("No period rows are available for the selected window.")

st.subheader("Per-Period Detail")
render_section_overview(
    "per_period_detail",
    section_context,
    model=section_model,
    api_key=section_api_key,
)
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
