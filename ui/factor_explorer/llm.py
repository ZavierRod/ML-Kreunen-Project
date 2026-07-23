"""OpenAI-backed analyst helpers for the GOOG Factor Explorer."""

from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd


DEFAULT_MODEL = "gpt-4o-mini"

ANALYST_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "name": "factor_analyst_answer",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "answer": {
                "type": "string",
                "description": (
                    "A multi-sentence analyst explanation grounded only in the "
                    "supplied factor data."
                ),
            },
            "supporting_points": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "metric": {"type": "string"},
                        "period": {"type": "string"},
                        "value": {"type": "string"},
                        "explanation": {"type": "string"},
                    },
                    "required": ["metric", "period", "value", "explanation"],
                },
            },
            "caveats": {
                "type": "array",
                "items": {"type": "string"},
            },
            "suggested_followups": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Two or three concise, standalone questions the user can ask next."
                ),
            },
        },
        "required": ["answer", "supporting_points", "caveats", "suggested_followups"],
    },
}

SECTION_OVERVIEW_KEYS = (
    "ranking_table",
    "visual_analysis",
    "period_drilldown",
    "per_period_detail",
)

_SECTION_OVERVIEW_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {
            "type": "string",
            "description": "A detailed, data-grounded explanation of the current section.",
        },
        "key_points": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Exactly three concrete observations from the supplied data.",
        },
        "how_to_read": {
            "type": "string",
            "description": "How a user should interpret the section and its measures.",
        },
        "caveat": {
            "type": "string",
            "description": "The most important limitation or interpretation warning.",
        },
    },
    "required": ["summary", "key_points", "how_to_read", "caveat"],
}

SECTION_OVERVIEW_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "name": "factor_section_overview",
    "strict": True,
    "schema": _SECTION_OVERVIEW_ITEM_SCHEMA,
}

_SECTION_OVERVIEW_GUIDANCE = {
    "ranking_table": (
        "Discuss leaders, direction, persistence, and weights when available. Explain "
        "that rank is based on mean absolute movement, not causal importance."
    ),
    "visual_analysis": (
        "Connect patterns across the ranking bar, weight evolution, heatmap, and preset "
        "benchmark views. Note when weights are unavailable."
    ),
    "period_drilldown": (
        "Focus on the exact selected period, its largest positive and negative moves, "
        "and relative weights when available."
    ),
    "per_period_detail": (
        "Explain cross-period patterns, outliers, missing values, the pct and weight "
        "columns, and the dominant-cell highlight."
    ),
}


def _secret_value(secrets: Any, key: str) -> str | None:
    try:
        value = secrets.get(key)
    except Exception:
        value = None
    if value is None:
        return None
    return str(value).strip() or None


def api_key_from_environment(secrets: Any | None = None) -> str | None:
    """Read the API key from Streamlit secrets first, then the shell env."""
    secret_key = _secret_value(secrets, "OPENAI_API_KEY") if secrets is not None else None
    return secret_key or os.environ.get("OPENAI_API_KEY")


def model_from_environment(secrets: Any | None = None) -> str:
    """Allow the app owner to swap models without code changes."""
    secret_model = _secret_value(secrets, "OPENAI_MODEL") if secrets is not None else None
    return secret_model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)


def _clean_value(value: object) -> object:
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float):
        return round(value, 6)
    return value


def _records(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, object]]:
    available = [column for column in columns if column in frame.columns]
    rows = []
    for raw in frame[available].to_dict("records"):
        rows.append({key: _clean_value(value) for key, value in raw.items()})
    return rows


def build_analysis_context(
    *,
    selected_metrics: list[str],
    start_year: int,
    end_year: int,
    panel: pd.DataFrame,
    ranking: pd.DataFrame,
    metric_catalog: dict[str, Any],
    conflicts: list[tuple[str, str]],
    weight_mode: bool,
    validation: list[dict[str, str]],
    brief: list[str],
) -> dict[str, object]:
    """Convert the current UI state into compact, model-readable context."""
    metric_definitions = []
    for metric in selected_metrics:
        spec = metric_catalog[metric]
        metric_definitions.append(
            {
                "name": spec.name,
                "type": spec.metric_type,
                "source_phase": spec.source_phase,
                "notes": spec.notes,
                "parents": sorted(spec.parents),
                "weightable": spec.weightable,
            }
        )

    panel_view = panel.copy()
    panel_view["abs_pct_change"] = pd.to_numeric(
        panel_view["pct_change"], errors="coerce"
    ).abs()

    largest_period_moves = panel_view.sort_values(
        "abs_pct_change", ascending=False, na_position="last"
    ).head(12)

    return {
        "scope": {
            "company": "GOOG",
            "selected_metrics": selected_metrics,
            "start_year": start_year,
            "end_year": end_year,
            "mode": "weighted" if weight_mode else "rank_only",
            "numeric_convention": (
                "Percentage and weight values are decimal fractions; multiply by 100 "
                "when writing them as percentages."
            ),
            "valid_periods": int(panel["period"].nunique()) if not panel.empty else 0,
            "double_count_conflicts": [
                {"derived_metric": derived, "input_metric": parent}
                for derived, parent in conflicts
            ],
        },
        "metric_definitions": metric_definitions,
        "ranking": _records(
            ranking,
            [
                "overall_rank",
                "metric",
                "type",
                "mean_abs",
                "mean",
                "mean_weight",
                "positive_periods",
                "negative_periods",
                "periods",
            ],
        ),
        "period_panel": _records(
            panel,
            [
                "from_year",
                "to_year",
                "period",
                "metric",
                "type",
                "pct_change",
                "weight",
            ],
        ),
        "largest_period_moves": _records(
            largest_period_moves,
            [
                "period",
                "metric",
                "type",
                "pct_change",
                "abs_pct_change",
                "weight",
            ],
        ),
        "validation": validation,
        "auto_brief": brief,
    }


def build_section_overview_context(
    *,
    analysis_context: dict[str, object],
    panel: pd.DataFrame,
    detail: pd.DataFrame,
    preset_comparison: pd.DataFrame,
    selected_period: str | None,
) -> dict[str, object]:
    """Add compact section-specific views to the shared analyst context."""
    period_rows = (
        panel[panel["period"] == selected_period]
        if selected_period is not None
        else panel.iloc[0:0]
    )
    context = dict(analysis_context)
    context["section_views"] = {
        "ranking_table": {
            "ranking_basis": "mean absolute year-over-year percentage change",
            "direction_measure": "mean signed year-over-year percentage change",
            "weight_measure": "mean share of total absolute movement when weighted mode is enabled",
        },
        "visual_analysis": {
            "available_views": [
                "mean absolute move ranking bar",
                "weight evolution area chart when weighted mode is enabled",
                "period-by-metric percentage-change heatmap",
                "preset benchmark comparison",
            ],
            "preset_comparison": _records(
                preset_comparison,
                [
                    "preset",
                    "factor_count",
                    "mode",
                    "top_metric",
                    "top_mean_abs",
                    "valid_periods",
                    "conflicts",
                ],
            ),
        },
        "period_drilldown": {
            "selected_period": selected_period,
            "rows": _records(
                period_rows,
                ["period", "metric", "type", "pct_change", "weight"],
            ),
        },
        "per_period_detail": {
            "row_count": int(len(detail)),
            "columns": [str(column) for column in detail.columns],
            "first_period": None if detail.empty else str(detail.iloc[0]["period"]),
            "last_period": None if detail.empty else str(detail.iloc[-1]["period"]),
            "dominant_cell_rule": (
                "The highlighted pct cell is the largest absolute selected-metric "
                "move in that row."
            ),
        },
    }
    return context


def context_for_section_overview(
    context: dict[str, object], section_key: str
) -> dict[str, object]:
    """Return only the context relevant to one manually requested overview."""
    if section_key not in SECTION_OVERVIEW_KEYS:
        raise ValueError(f"Unknown section overview: {section_key}")

    section_views = context.get("section_views", {})
    if not isinstance(section_views, dict):
        section_views = {}

    scoped = {
        key: context[key]
        for key in (
            "scope",
            "metric_definitions",
            "ranking",
            "largest_period_moves",
            "auto_brief",
        )
        if key in context
    }
    if section_key in {"visual_analysis", "per_period_detail"}:
        scoped["period_panel"] = context.get("period_panel", [])
    scoped["section_view"] = section_views.get(section_key, {})
    return scoped


def answer_question(
    *,
    question: str,
    context: dict[str, object],
    api_key: str,
    model: str,
) -> dict[str, object]:
    """Ask the OpenAI Responses API for a structured, data-grounded answer."""
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - depends on the local environment.
        raise RuntimeError(
            "The openai package is not installed. Run `pip install -r requirements.txt`, "
            "then restart Streamlit."
        ) from exc

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        instructions=(
            "You are a careful finance data analyst embedded in a Streamlit app. "
            "Answer only from the supplied GOOG factor explorer context. "
            "Write the main answer as a short analyst-style explanation, usually "
            "2-4 sentences and roughly 80-160 words. Do not collapse the response "
            "into one sentence unless the user explicitly asks for one. "
            "Explain the why, not just the what. "
            "Cite metrics, periods, and values from the context in supporting_points. "
            "Include 2-5 supporting_points when the data supports them. "
            "Provide 2-3 suggested_followups as complete, standalone questions that "
            "can be submitted directly without rewriting. "
            "If the context does not support the answer, say what is missing. "
            "Do not provide investment advice or make claims about future stock performance."
        ),
        input=(
            "User question:\n"
            f"{question}\n\n"
            "Current factor explorer context as JSON:\n"
            f"{json.dumps(context, separators=(',', ':'), ensure_ascii=True)}"
        ),
        text={"format": ANALYST_SCHEMA},
        max_output_tokens=1800,
    )

    raw_text = response.output_text
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Model returned invalid JSON: {raw_text}") from exc
    return parsed


def generate_section_overview(
    *,
    section_key: str,
    context: dict[str, object],
    api_key: str,
    model: str,
) -> dict[str, object]:
    """Generate one section explanation after an explicit user action."""
    if section_key not in SECTION_OVERVIEW_KEYS:
        raise ValueError(f"Unknown section overview: {section_key}")

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - depends on the local environment.
        raise RuntimeError(
            "The openai package is not installed. Run `pip install -r requirements.txt`, "
            "then restart Streamlit."
        ) from exc

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        instructions=(
            "You are a careful finance data analyst writing inline guidance for a "
            "GOOG factor explorer. Produce the requested section overview from only "
            "the supplied context. The summary should be 80-140 words, explain "
            "the current result rather than merely define the UI, and use plain language. "
            "Return exactly three concise key_points. In how_to_read, explain "
            "what the measures mean and how the section relates to the current selection. "
            "Use caveat for the most material limitation, including missing values, "
            "rank-only mode, overlap, or the fact that magnitude is not causal importance. "
            f"Section-specific guidance: {_SECTION_OVERVIEW_GUIDANCE[section_key]} "
            "Never provide investment advice or forecast "
            "stock performance. Do not invent values or external explanations."
            " Apply the numeric convention in scope and write decimal fraction values "
            "as percentages."
        ),
        input=(
            f"Requested section: {section_key}\n"
            "Current factor explorer context as JSON:\n"
            f"{json.dumps(context, separators=(',', ':'), ensure_ascii=True)}"
        ),
        text={"format": SECTION_OVERVIEW_SCHEMA},
        max_output_tokens=1000,
    )

    raw_text = response.output_text
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Model returned invalid section overview JSON: {raw_text}") from exc
    return parsed
