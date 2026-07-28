"""Local Streamlit workflow for configurable one-month excess-return forecasts."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from excess_return_engine.experiments import (
    comparison_label,
    comparison_warnings,
    list_experiments,
    save_experiment,
)
from excess_return_engine.features import FACTOR_IDS, FACTOR_REGISTRY
from excess_return_engine.model import (
    ForecastRequest,
    generate_forecast,
    save_forecast_result,
)
from excess_return_engine.replay import (
    available_as_of_dates,
    build_as_of_snapshot,
    realized_replay_outcome,
)
from ui.excess_return_engine import analyst
from ui.excess_return_engine.presentation import (
    FACTOR_PRESETS,
    apply_pending_saved_configuration,
    calibration_table,
    challenger_diagnostics_table,
    company_options,
    configuration_quality,
    correlation_warning_table,
    contribution_table,
    factor_option_label,
    experiment_comparison_table,
    experiment_contribution_table,
    historical_analog_table,
    predictive_strength_label,
    queue_saved_configuration,
    reliability_component_table,
    regime_summary,
    regime_table,
    yearly_validation_table,
)

DEFAULT_ARTIFACT_DIR = ROOT / "local_artifacts" / "excess_return_engine"
ARTIFACT_DIR = Path(
    os.getenv("EXCESS_RETURN_ARTIFACT_DIR", str(DEFAULT_ARTIFACT_DIR))
).expanduser()
EXPERIMENT_DIR = ARTIFACT_DIR / "experiments"
ALL_HISTORY_OPTION = "all_available"
TRAINING_WINDOW_OPTIONS = (ALL_HISTORY_OPTION, 120, 144)

st.set_page_config(
    page_title="One-Month Excess Return",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 2.5rem; padding-bottom: 3rem;}
    [data-testid="stMetric"] {
        border-top: 2px solid #d1d5db;
        padding-top: 0.65rem;
    }
    [data-testid="stMetricValue"] {font-size: 1.65rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def load_research_panels(artifact_dir: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    directory = Path(artifact_dir)
    training_path = directory / "training_panel.parquet"
    inference_path = directory / "inference_panel.parquet"
    if not training_path.is_file() or not inference_path.is_file():
        raise FileNotFoundError(
            "The local training and inference panels have not been built."
        )
    return pd.read_parquet(training_path), pd.read_parquet(inference_path)


def format_percent(value: float, digits: int = 1) -> str:
    return f"{value * 100:+.{digits}f}%"


def format_probability(value: float) -> str:
    return f"{value * 100:.1f}%"


def format_training_window(value: int | str | None) -> str:
    if value is None or value == ALL_HISTORY_OPTION:
        return "All available"
    months = int(value)
    return f"{months // 12} years · {months} months"


def contribution_chart(table: pd.DataFrame) -> go.Figure:
    data = table.sort_values("contribution")
    colors = ["#b91c1c" if value < 0 else "#047857" for value in data["contribution"]]
    figure = go.Figure(
        go.Bar(
            x=data["contribution"] * 100,
            y=data["factor"],
            orientation="h",
            marker_color=colors,
            text=(data["contribution"] * 100).map(lambda value: f"{value:+.2f}%"),
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b><br>Contribution: %{x:+.3f}%<extra></extra>"
            ),
        )
    )
    figure.add_vline(x=0, line_color="#6b7280", line_width=1)
    figure.update_layout(
        height=max(320, 52 * len(data)),
        margin=dict(l=10, r=70, t=15, b=35),
        xaxis_title="Contribution to expected excess return (%)",
        yaxis_title=None,
        showlegend=False,
    )
    return figure


def calibration_chart(table: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=table["Mean predicted probability"] * 100,
            y=table["Observed positive rate"] * 100,
            mode="lines+markers",
            name="Holdout bins",
            line=dict(color="#dc2626", width=2),
            marker=dict(size=8),
            hovertemplate=(
                "Predicted: %{x:.1f}%<br>Observed: %{y:.1f}%<extra></extra>"
            ),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=[0, 100],
            y=[0, 100],
            mode="lines",
            name="Perfect calibration",
            line=dict(color="#6b7280", dash="dash"),
            hoverinfo="skip",
        )
    )
    figure.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=20, b=40),
        xaxis_title="Mean predicted positive probability (%)",
        yaxis_title="Observed positive excess-return rate (%)",
        xaxis=dict(range=[0, 100]),
        yaxis=dict(range=[0, 100]),
        legend=dict(orientation="h", y=1.08),
    )
    return figure


def experiment_contribution_chart(table: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    for experiment, group in table.groupby("Experiment", sort=False):
        figure.add_trace(
            go.Bar(
                name=experiment,
                x=group["Factor"],
                y=group["Contribution"] * 100,
                hovertemplate=(
                    "<b>%{x}</b><br>Contribution: %{y:+.3f}%<extra></extra>"
                ),
            )
        )
    figure.add_hline(y=0, line_color="#6b7280", line_width=1)
    figure.update_layout(
        barmode="group",
        height=390,
        margin=dict(l=20, r=20, t=20, b=90),
        xaxis_title=None,
        yaxis_title="Contribution to expected excess return (%)",
        legend=dict(orientation="h", y=1.10),
    )
    return figure


def render_experiment_workspace(result) -> None:
    st.divider()
    st.subheader("Saved Experiments")

    saved_message = st.session_state.pop("experiment_saved_message", None)
    if saved_message:
        st.success(saved_message)

    save_columns = st.columns([3, 1])
    with save_columns[0]:
        experiment_name = st.text_input(
            "Experiment name",
            value=f"{result.ticker} · {len(result.selected_factors)} factors",
            key=f"experiment_name_{result.configuration_id}",
            max_chars=80,
        )
    with save_columns[1]:
        st.write("")
        st.write("")
        save_clicked = st.button(
            "Save experiment",
            icon=":material/bookmark_add:",
            key=f"save_experiment_{result.configuration_id}",
            width="stretch",
        )
    if save_clicked:
        try:
            experiment, _ = save_experiment(
                result,
                experiment_name,
                EXPERIMENT_DIR,
            )
            st.session_state["experiment_saved_message"] = (
                f"Saved {experiment.name} · run {experiment.configuration_id}."
            )
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    experiments = list_experiments(EXPERIMENT_DIR)
    if not experiments:
        st.caption("No named experiments saved yet.")
        return

    experiment_lookup = {
        item.experiment_id: item for item in experiments
    }
    current_matches = [
        item.experiment_id
        for item in experiments
        if item.configuration_id == result.configuration_id
    ]
    default_ids = current_matches[:1]
    default_ids.extend(
        item.experiment_id
        for item in experiments
        if item.experiment_id not in default_ids
    )
    default_ids = default_ids[:2]
    selected_ids = st.multiselect(
        "Compare experiments",
        options=list(experiment_lookup),
        default=default_ids,
        format_func=lambda experiment_id: comparison_label(
            experiment_lookup[experiment_id]
        ),
        key=f"experiment_comparison_{result.configuration_id}",
    )
    selected = tuple(
        experiment_lookup[experiment_id] for experiment_id in selected_ids
    )
    if len(selected) < 2:
        st.caption("Select at least two saved experiments for comparison.")
        return

    for warning in comparison_warnings(selected):
        st.warning(warning)

    comparison = experiment_comparison_table(selected)
    st.dataframe(
        comparison.style.format(
            {
                "Expected excess return": "{:+.2%}",
                "Expected-return delta vs first": "{:+.2%}",
                "Probability positive": "{:.1%}",
                "Probability delta vs first": "{:+.1%}",
                "Interval width": "{:.2%}",
                "Model reliability": "{:.0f}/100",
                "Data quality": "{:.0f}/100",
                "OOS R² vs zero": "{:+.2%}",
                "Interval coverage": "{:.1%}",
                "Production RMSE": "{:.2%}",
            },
            na_rep="Not recorded",
        ),
        hide_index=True,
        width="stretch",
    )
    contribution_comparison = experiment_contribution_table(selected)
    st.plotly_chart(
        experiment_contribution_chart(contribution_comparison),
        width="stretch",
        config={"displayModeBar": False},
    )
    st.download_button(
        "Download comparison CSV",
        data=comparison.to_csv(index=False).encode(),
        file_name=f"experiment_comparison_{result.target_month}.csv",
        mime="text/csv",
        icon=":material/download:",
    )


def render_forecast_analyst_answer(answer: dict[str, object]) -> None:
    st.markdown(str(answer.get("answer", "")))
    st.caption(f"Forecast run: `{answer.get('forecast_run_id', '')}`")
    if answer.get("generation_mode") == "deterministic_policy_fallback":
        st.caption(
            "The model draft did not pass evidence-language checks; this answer "
            "uses the deterministic forecast summary."
        )

    supporting_points = answer.get("supporting_points", [])
    if isinstance(supporting_points, list) and supporting_points:
        st.markdown("**Supporting evidence**")
        for point in supporting_points:
            if not isinstance(point, dict):
                continue
            st.markdown(
                f"**{point.get('label', '')}:** {point.get('value', '')}"
            )
            st.caption(
                f"{point.get('explanation', '')} "
                f"Source: {str(point.get('evidence_source', '')).replace('_', ' ')}."
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
                key=(
                    f"forecast_analyst_followup_"
                    f"{answer.get('forecast_run_id', '')}_{index}"
                ),
                width="stretch",
            ):
                st.session_state["forecast_analyst_pending_question"] = followup_text
                st.rerun()


def render_forecast_analyst(
    result,
    replay_outcome=None,
) -> None:
    st.divider()
    st.subheader("Ask the Forecast")

    if st.session_state.get("forecast_analyst_run_id") != result.configuration_id:
        st.session_state["forecast_analyst_run_id"] = result.configuration_id
        for key in (
            "forecast_analyst_answer",
            "forecast_analyst_error",
            "forecast_analyst_pending_question",
            "forecast_analyst_question",
        ):
            st.session_state.pop(key, None)

    pending = st.session_state.pop("forecast_analyst_pending_question", None)
    auto_submit = isinstance(pending, str) and bool(pending.strip())
    if auto_submit:
        st.session_state["forecast_analyst_question"] = pending.strip()
    if "forecast_analyst_question" not in st.session_state:
        st.session_state["forecast_analyst_question"] = (
            "What is the clearest takeaway from this forecast?"
        )

    examples = [
        "Why does the model expect this excess return?",
        "What makes this forecast uncertain?",
        "What were the excess-return outcomes in similar historical conditions?",
    ]
    example_columns = st.columns(3)
    for column, example in zip(example_columns, examples):
        with column:
            if st.button(
                example,
                key=f"forecast_analyst_example_{examples.index(example)}",
                width="stretch",
            ):
                st.session_state["forecast_analyst_question"] = example

    question = st.text_area(
        "Question",
        key="forecast_analyst_question",
        height=90,
        max_chars=analyst.MAX_QUESTION_LENGTH,
    )
    api_key = analyst.api_key_from_environment(st.secrets)
    model = analyst.model_from_environment(st.secrets)
    include_analog_rows = analyst.include_analog_rows_from_environment(st.secrets)

    if not api_key:
        st.info(
            "Set `OPENAI_API_KEY` in local Streamlit secrets to enable forecast questions."
        )
    else:
        evidence_scope = (
            "aggregate evidence plus individual analog rows"
            if include_analog_rows
            else "aggregate evidence; individual analog rows excluded"
        )
        st.caption(f"Model: `{model}` · API evidence: {evidence_scope}")

    action_columns = st.columns([1, 1, 4])
    with action_columns[0]:
        ask_clicked = st.button(
            "Ask analyst",
            type="primary",
            icon=":material/chat:",
            disabled=not api_key or not question.strip(),
        )
    with action_columns[1]:
        if st.button("Clear answer"):
            st.session_state.pop("forecast_analyst_answer", None)
            st.session_state.pop("forecast_analyst_error", None)

    if (ask_clicked or auto_submit) and api_key:
        context = analyst.build_forecast_context(
            result,
            include_analog_rows=include_analog_rows,
            replay_outcome=replay_outcome,
        )
        with st.spinner("Analyzing this forecast run..."):
            try:
                answer = analyst.answer_forecast_question(
                    question=question,
                    context=context,
                    api_key=api_key,
                    model=model,
                )
                analyst.save_analyst_exchange(
                    output_dir=ARTIFACT_DIR / "analyst_exchanges",
                    forecast_run_id=result.configuration_id,
                    question=question,
                    model=model,
                    include_analog_rows=include_analog_rows,
                    answer=answer,
                )
                st.session_state["forecast_analyst_answer"] = answer
                st.session_state.pop("forecast_analyst_error", None)
            except Exception as exc:
                st.session_state["forecast_analyst_error"] = str(exc)

    if st.session_state.get("forecast_analyst_error"):
        st.error(st.session_state["forecast_analyst_error"])
    if st.session_state.get("forecast_analyst_answer"):
        render_forecast_analyst_answer(
            st.session_state["forecast_analyst_answer"]
        )


st.title("One-Month Excess Return")

try:
    training_panel, inference_panel = load_research_panels(str(ARTIFACT_DIR))
except Exception as exc:
    st.error(str(exc))
    st.caption(f"Expected local artifact directory: {ARTIFACT_DIR}")
    st.stop()

latest_as_of = pd.Timestamp(inference_panel["month_end"].max())
as_of_dates = available_as_of_dates(training_panel, inference_panel)
as_of_lookup = {
    item.date().isoformat(): item
    for item in reversed(as_of_dates)
}
latest_as_of_key = latest_as_of.date().isoformat()
apply_pending_saved_configuration(st.session_state)
st.session_state.setdefault("forecast_as_of", latest_as_of_key)
if st.session_state["forecast_as_of"] not in as_of_lookup:
    st.session_state["forecast_as_of"] = latest_as_of_key

with st.sidebar:
    st.header("Forecast Configuration")
    selected_as_of_key = st.selectbox(
        "As-of date",
        options=list(as_of_lookup),
        key="forecast_as_of",
        format_func=lambda value: (
            f"Latest · {value}"
            if value == latest_as_of_key
            else value
        ),
    )

as_of = as_of_lookup[selected_as_of_key]
inference_snapshot = build_as_of_snapshot(
    training_panel,
    inference_panel,
    as_of,
)
target_month = pd.Timestamp(inference_snapshot["target_month"].max())
benchmark_ids = (
    inference_snapshot["benchmark_id"].dropna().astype(str).unique()
)
benchmark_id = benchmark_ids[0] if len(benchmark_ids) == 1 else "Multiple benchmarks"

options = company_options(inference_snapshot)
option_lookup = dict(options)
default_company = next(
    (label for label, _ in options if label.startswith("GOOGL ·")),
    options[0][0],
)
saved_experiments = list_experiments(EXPERIMENT_DIR)
available_training_months = int(
    training_panel.loc[
        pd.to_datetime(training_panel["month_end"]) < as_of,
        "month_end",
    ].nunique()
)
training_window_options = tuple(
    option
    for option in TRAINING_WINDOW_OPTIONS
    if option == ALL_HISTORY_OPTION or int(option) <= available_training_months
)

with st.sidebar:
    if saved_experiments:
        saved_lookup = {
            item.experiment_id: item for item in saved_experiments
        }
        saved_choice = st.selectbox(
            "Saved configuration",
            options=list(saved_lookup),
            format_func=lambda experiment_id: comparison_label(
                saved_lookup[experiment_id]
            ),
            key="saved_configuration_choice",
        )
        if st.button(
            "Apply saved configuration",
            icon=":material/settings_backup_restore:",
            width="stretch",
        ):
            saved = saved_lookup[saved_choice]
            if saved.as_of_date not in as_of_lookup:
                st.error(
                    "The saved as-of date is not available in the loaded "
                    "research panels."
                )
            else:
                saved_as_of = as_of_lookup[saved.as_of_date]
                saved_snapshot = build_as_of_snapshot(
                    training_panel,
                    inference_panel,
                    saved_as_of,
                )
                saved_options = company_options(saved_snapshot)
                saved_company = next(
                    (
                        label
                        for label, saved_permno in saved_options
                        if saved_permno == saved.permno
                    ),
                    None,
                )
                saved_available_months = int(
                    training_panel.loc[
                        pd.to_datetime(training_panel["month_end"])
                        < saved_as_of,
                        "month_end",
                    ].nunique()
                )
                if saved_company is None:
                    st.error(
                        "The saved security is not available at its saved "
                        "as-of date."
                    )
                elif (
                    saved.training_window_months is not None
                    and saved.training_window_months > saved_available_months
                ):
                    st.error(
                        "The saved training window is not available at its "
                        "saved as-of date."
                    )
                else:
                    queue_saved_configuration(
                        st.session_state,
                        saved,
                        saved_company,
                    )
                    st.rerun()
        st.divider()

    st.session_state.setdefault("forecast_company", default_company)
    if st.session_state["forecast_company"] not in option_lookup:
        st.session_state["forecast_company"] = default_company
    selected_company = st.selectbox(
        "Company",
        options=[label for label, _ in options],
        key="forecast_company",
    )
    permno = option_lookup[selected_company]

    st.session_state.setdefault("forecast_preset", "Balanced")
    preset = st.segmented_control(
        "Factor preset",
        options=list(FACTOR_PRESETS),
        key="forecast_preset",
        width="stretch",
    )
    preset_key = preset
    if (
        preset_key is not None
        and st.session_state.get("_last_forecast_preset") != preset_key
    ):
        st.session_state["forecast_factors"] = list(FACTOR_PRESETS[preset_key])
        st.session_state["_last_forecast_preset"] = preset_key

    selected_factors = st.multiselect(
        "Selected factors",
        options=list(FACTOR_IDS),
        key="forecast_factors",
        format_func=factor_option_label,
    )
    st.session_state.setdefault("forecast_interval", 0.80)
    interval_level = st.select_slider(
        "Prediction interval",
        options=[0.70, 0.80, 0.90],
        key="forecast_interval",
        format_func=lambda value: f"{value:.0%}",
    )
    st.session_state.setdefault(
        "forecast_training_window",
        ALL_HISTORY_OPTION,
    )
    if (
        st.session_state["forecast_training_window"]
        not in training_window_options
    ):
        st.session_state["forecast_training_window"] = ALL_HISTORY_OPTION
    selected_training_window = st.selectbox(
        "Training window",
        options=training_window_options,
        key="forecast_training_window",
        format_func=format_training_window,
    )
    training_window_months = (
        None
        if selected_training_window == ALL_HISTORY_OPTION
        else int(selected_training_window)
    )

    st.divider()
    st.caption(f"As of {as_of.date().isoformat()}")
    st.caption(f"Target month {target_month.date().isoformat()}")
    st.caption(f"Benchmark {benchmark_id}")

applied_message = st.session_state.pop("applied_experiment_message", None)
if applied_message:
    st.success(applied_message)

quality = configuration_quality(
    training_panel,
    inference_snapshot,
    permno,
    tuple(selected_factors),
    training_window_months=training_window_months,
    as_of_date=as_of,
)

config_columns = st.columns(4)
config_columns[0].metric("Selected factors", len(selected_factors))
config_columns[1].metric("Training months", int(quality["training_months"]))
config_columns[2].metric(
    "Current completeness",
    format_probability(float(quality["current_completeness"])),
)
config_columns[3].metric(
    "Historical coverage",
    format_probability(float(quality["historical_coverage"])),
)

if quality["status"] == "blocked":
    st.error(str(quality["message"]))
else:
    st.caption(str(quality["message"]))
if quality["correlated_pairs"]:
    st.warning(
        "Selected factors include correlations of at least 0.85. Run-level "
        "reliability will report the affected pairs."
    )

run_forecast = st.button(
    "Run forecast",
    type="primary",
    icon=":material/query_stats:",
    disabled=quality["status"] != "ready",
)

if run_forecast:
    request = ForecastRequest(
        permno=permno,
        selected_factors=tuple(selected_factors),
        as_of_date=as_of.date().isoformat(),
        interval_level=interval_level,
        training_window_months=training_window_months,
    )
    with st.spinner("Fitting selected-factor model and calibrating uncertainty..."):
        try:
            generated_result = generate_forecast(
                training_panel,
                inference_snapshot,
                request,
            )
            save_forecast_result(
                generated_result,
                ARTIFACT_DIR / "forecast_runs",
            )
            st.session_state["excess_return_result"] = generated_result
            st.session_state.pop("excess_return_error", None)
        except Exception as exc:
            st.session_state["excess_return_error"] = str(exc)

if st.session_state.get("excess_return_error"):
    st.error(st.session_state["excess_return_error"])

result = st.session_state.get("excess_return_result")
result_matches_configuration = (
    result is not None
    and result.permno == permno
    and result.selected_factors == tuple(selected_factors)
    and result.as_of_date == as_of.date().isoformat()
    and result.snapshot_source
    == inference_snapshot.attrs["snapshot_source"]
    and result.interval_level == interval_level
    and getattr(result, "training_window_months", None) == training_window_months
)
if not result_matches_configuration:
    st.subheader("Configuration")
    selected_table = pd.DataFrame(
        [
            {
                "Factor": FACTOR_REGISTRY[factor].label,
                "Category": FACTOR_REGISTRY[factor].category,
                "Availability": FACTOR_REGISTRY[factor].availability_rule,
            }
            for factor in selected_factors
        ]
    )
    st.dataframe(selected_table, hide_index=True, width="stretch")
    st.stop()

st.subheader(f"{result.ticker} Forecast")
headline = st.columns(4)
headline[0].metric(
    "Expected excess return",
    format_percent(result.expected_excess_return),
)
headline[1].metric(
    "Probability positive",
    format_probability(result.probability_positive),
)
headline[2].metric(
    f"{result.interval_level:.0%} prediction interval",
    (
        f"{format_percent(result.interval_lower)} to "
        f"{format_percent(result.interval_upper)}"
    ),
)
headline[3].metric(
    "Model reliability",
    (
        f"{result.reliability.model_reliability_label} · "
        f"{result.reliability.model_reliability_score:.0f}/100"
    ),
)

st.caption(
    f"Benchmark: {result.benchmark_id} · As of: {result.as_of_date} · "
    f"Target: {result.target_month} · Training: "
    f"{format_training_window(getattr(result, 'training_window_months', None))} · "
    f"Mode: "
    f"{'Historical replay' if result.snapshot_source == 'historical_replay' else 'Latest snapshot'} "
    f"· "
    f"Run: {result.configuration_id}"
)
replay_outcome = None
if result.snapshot_source == "historical_replay":
    replay_outcome = realized_replay_outcome(
        training_panel,
        result.permno,
        result.as_of_date,
    )
    if replay_outcome is not None:
        st.markdown("**Replay outcome · revealed after forecast generation**")
        replay_columns = st.columns(4)
        replay_columns[0].metric(
            "Realized excess return",
            format_percent(replay_outcome.realized_excess_return),
        )
        replay_columns[1].metric(
            "Forecast error",
            format_percent(
                result.expected_excess_return
                - replay_outcome.realized_excess_return
            ),
        )
        replay_columns[2].metric(
            "Realized stock return",
            format_percent(replay_outcome.realized_stock_return),
        )
        replay_columns[3].metric(
            "Realized benchmark return",
            format_percent(replay_outcome.realized_benchmark_return),
        )
        st.caption(
            "The realized outcome was excluded from the inference snapshot "
            "and model fit, then joined back only for replay evaluation."
        )

contributions = contribution_table(result)
contribution_tab, evidence_tab, reliability_tab, validation_tab, data_tab = st.tabs(
    [
        "Contributions",
        "Regime & analogs",
        "Reliability",
        "Validation",
        "Data quality",
    ]
)
with contribution_tab:
    left, right = st.columns([1.25, 0.75])
    with left:
        st.plotly_chart(
            contribution_chart(contributions),
            width="stretch",
            config={"displayModeBar": False},
        )
    with right:
        display = contributions[
            ["factor", "category", "normalized_value", "coefficient", "contribution"]
        ].copy()
        display.columns = [
            "Factor",
            "Category",
            "Normalized value",
            "Coefficient",
            "Contribution",
        ]
        st.dataframe(
            display.style.format(
                {
                    "Normalized value": "{:+.3f}",
                    "Coefficient": "{:+.4f}",
                    "Contribution": "{:+.2%}",
                }
            ),
            hide_index=True,
            width="stretch",
            height=390,
        )
with evidence_tab:
    st.subheader("Current factor regime")
    st.caption(regime_summary(result))
    st.dataframe(
        regime_table(result).style.format({"Percentile": "{:.0%}"}),
        hide_index=True,
        width="stretch",
    )

    evidence = result.historical_evidence
    st.subheader("Historical outcomes under similar conditions")
    evidence_columns = st.columns(4)
    evidence_columns[0].metric(
        "Mean excess return",
        format_percent(evidence.mean_excess_return),
    )
    evidence_columns[1].metric(
        "Median excess return",
        format_percent(evidence.median_excess_return),
    )
    evidence_columns[2].metric(
        "Positive outcomes",
        format_probability(evidence.probability_positive),
    )
    evidence_columns[3].metric(
        "10th–90th percentile",
        (
            f"{format_percent(evidence.tenth_percentile)} to "
            f"{format_percent(evidence.ninetieth_percentile)}"
        ),
    )
    st.caption(
        f"{evidence.neighbor_count} nearest historical security-months in the "
        "selected normalized factor space."
    )
    st.dataframe(
        historical_analog_table(result).style.format(
            {
                "Similarity": "{:.1%}",
                "Observed excess return": "{:+.2%}",
            }
        ),
        hide_index=True,
        width="stretch",
        height=390,
    )
with reliability_tab:
    reliability = result.reliability
    reliability_columns = st.columns(4)
    reliability_columns[0].metric(
        "Model reliability",
        f"{reliability.model_reliability_score:.0f}/100",
    )
    reliability_columns[1].metric(
        "Data quality",
        f"{reliability.data_quality_score:.0f}/100",
    )
    reliability_columns[2].metric(
        "Training-distance percentile",
        f"{reliability.current_distance_percentile:.0%}",
    )
    reliability_columns[3].metric(
        "Close historical analogs",
        reliability.close_analog_count,
    )
    st.caption(
        f"{reliability.current_distance_status} · Nearest similarity "
        f"{reliability.nearest_similarity:.1%}"
    )
    st.dataframe(
        reliability_component_table(result).style.format({"Score": "{:.0f}/100"}),
        hide_index=True,
        width="stretch",
    )
    for warning in reliability.warnings:
        st.warning(warning)
    correlations = correlation_warning_table(result)
    if not correlations.empty:
        st.markdown("**Highly correlated selected factors**")
        st.dataframe(
            correlations.style.format({"Correlation": "{:+.2f}"}),
            hide_index=True,
            width="stretch",
        )
with validation_tab:
    metrics = result.validation_metrics
    validation_columns = st.columns(4)
    validation_columns[0].metric("Holdout MAE", format_probability(float(metrics["mae"])))
    validation_columns[1].metric("Holdout RMSE", format_probability(float(metrics["rmse"])))
    validation_columns[2].metric(
        "Directional hit rate",
        format_probability(float(metrics["directional_hit_rate"])),
    )
    validation_columns[3].metric(
        "Interval coverage",
        format_probability(float(metrics["interval_coverage"])),
    )
    st.dataframe(
        pd.DataFrame(
            [
                {"Metric": "Brier score", "Value": float(metrics["brier_score"])},
                {
                    "Metric": "OOS R² vs zero",
                    "Value": float(metrics["oos_r2_vs_zero"]),
                },
                {
                    "Metric": "Evaluation observations",
                    "Value": int(metrics["evaluation_rows"]),
                },
                {
                    "Metric": "Evaluation months",
                    "Value": int(metrics["evaluation_months"]),
                },
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "Predictive strength: "
        f"{predictive_strength_label(result.validation_metrics)}"
    )
    calibration = calibration_table(result)
    calibration_left, calibration_right = st.columns([1.2, 0.8])
    with calibration_left:
        st.plotly_chart(
            calibration_chart(calibration),
            width="stretch",
            config={"displayModeBar": False},
        )
    with calibration_right:
        calibration_display = calibration[
            [
                "Bin",
                "Rows",
                "Mean predicted probability",
                "Observed positive rate",
            ]
        ]
        st.dataframe(
            calibration_display.style.format(
                {
                    "Mean predicted probability": "{:.1%}",
                    "Observed positive rate": "{:.1%}",
                }
            ),
            hide_index=True,
            width="stretch",
            height=360,
        )
    st.markdown("**Validation by outcome year**")
    yearly_validation = yearly_validation_table(result)
    st.dataframe(
        yearly_validation.style.format(
            {
                "MAE": "{:.2%}",
                "RMSE": "{:.2%}",
                "Directional hit rate": "{:.1%}",
                "Interval coverage": "{:.1%}",
                "Mean actual excess return": "{:+.2%}",
                "Mean predicted excess return": "{:+.2%}",
            }
        ),
        hide_index=True,
        width="stretch",
    )
    st.markdown("**Challenger model comparison**")
    st.caption(
        "All models are scored on the same untouched holdout. Challenger "
        "training is deterministically capped; only Elastic Net produces the "
        "forecast and factor attribution."
    )
    challenger_comparison = challenger_diagnostics_table(result)
    challenger_metrics = {
        item.model_id: item
        for item in result.challenger_diagnostics.metrics
    }
    leader_metric = challenger_metrics[
        result.challenger_diagnostics.leader_model_id
    ]
    production_metric = challenger_metrics["elastic_net"]
    if leader_metric.model_id == "elastic_net":
        st.success("Production Elastic Net has the lowest holdout RMSE.")
    else:
        st.warning(
            f"{leader_metric.label} has the lowest holdout RMSE, beating "
            "production Elastic Net by "
            f"{production_metric.rmse - leader_metric.rmse:.3%}. "
            "The production model is retained for its regularized, directly "
            "reconcilable attribution until the challenger advantage is "
            "repeatable across windows and regimes."
        )
    st.dataframe(
        challenger_comparison.style.format(
            {
                "Training rows": "{:,.0f}",
                "Evaluation rows": "{:,.0f}",
                "MAE": "{:.2%}",
                "RMSE": "{:.2%}",
                "RMSE vs production": "{:+.2%}",
                "Directional hit rate": "{:.1%}",
                "OOS R² vs zero": "{:+.2%}",
            }
        ),
        hide_index=True,
        width="stretch",
    )
with data_tab:
    quality_rows = [
        {"Component": key.replace("_", " ").title(), "Value": str(value)}
        for key, value in result.data_quality.items()
    ]
    st.dataframe(pd.DataFrame(quality_rows), hide_index=True, width="stretch")
    st.caption(
        f"Data: {result.data_version} · Target: {result.target_version} · "
        f"Features: {result.feature_version} · Model: {result.model_version} · "
        f"Reliability: {result.reliability_version} · "
        f"Validation: {result.validation_version} · "
        f"Challengers: {result.challenger_version} · "
        f"Replay: {result.replay_version or 'not applicable'}"
    )

render_experiment_workspace(result)
render_forecast_analyst(result, replay_outcome=replay_outcome)

st.download_button(
    "Download forecast JSON",
    data=(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n").encode(),
    file_name=f"{result.ticker}_{result.target_month}_excess_return.json",
    mime="application/json",
    icon=":material/download:",
)

st.warning(
    "Research output. The benchmark is the lagged-cap-weighted covered universe, "
    "fundamental timing uses the documented research lag proxy, and explicit "
    "delisting-return integration remains pending."
)
