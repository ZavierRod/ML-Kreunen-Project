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
            },
        },
        "required": ["answer", "supporting_points", "caveats", "suggested_followups"],
    },
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
