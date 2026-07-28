"""Local saved-experiment manifests and comparison records."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .model import ForecastResult

EXPERIMENT_VERSION = "saved-experiment-v8"
SUPPORTED_EXPERIMENT_VERSIONS = {
    "saved-experiment-v1",
    "saved-experiment-v2",
    "saved-experiment-v3",
    "saved-experiment-v4",
    "saved-experiment-v5",
    "saved-experiment-v6",
    "saved-experiment-v7",
    EXPERIMENT_VERSION,
}
MAX_EXPERIMENT_NAME_LENGTH = 80


@dataclass(frozen=True)
class SavedContribution:
    factor_id: str
    contribution: float


@dataclass(frozen=True)
class SavedExperiment:
    experiment_id: str
    experiment_version: str
    name: str
    saved_at: str
    configuration_id: str
    permno: int
    ticker: str | None
    company: str | None
    as_of_date: str
    snapshot_source: str
    replay_version: str | None
    target_month: str
    benchmark_id: str
    benchmark_version: str | None
    benchmark_label: str | None
    benchmark_method: str | None
    selected_factors: tuple[str, ...]
    training_window_months: int | None
    interval_level: float
    expected_excess_return: float
    probability_positive: float
    interval_lower: float
    interval_upper: float
    model_reliability_score: float
    model_reliability_label: str
    data_quality_score: float
    data_quality_label: str
    oos_r2_vs_zero: float
    interval_coverage: float
    contributions: tuple[SavedContribution, ...]
    data_version: str
    feature_version: str
    target_version: str
    model_version: str
    reliability_version: str
    validation_version: str
    challenger_version: str | None
    challenger_leader_model_id: str | None
    production_rmse: float | None
    production_rmse_rank: int | None
    walk_forward_version: str | None
    walk_forward_rmse: float | None
    walk_forward_oos_r2: float | None
    walk_forward_directional_hit_rate: float | None
    walk_forward_interval_coverage: float | None
    walk_forward_mean_rank_ic: float | None
    lineage_version: str | None
    factor_lineage_status: str | None
    factor_freshness_score: float | None
    stale_factor_count: int | None
    aging_factor_count: int | None
    research_proxy_factor_count: int | None
    audit_version: str | None
    panel_audit_id: str | None
    panel_audit_status: str | None
    audit_blocking_issue_count: int | None
    audit_review_issue_count: int | None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["selected_factors"] = list(self.selected_factors)
        payload["contributions"] = [
            asdict(contribution) for contribution in self.contributions
        ]
        return payload


def save_experiment(
    result: ForecastResult,
    name: str,
    output_dir: str | Path,
    *,
    saved_at: datetime | None = None,
) -> tuple[SavedExperiment, Path]:
    clean_name = _validate_name(name)
    timestamp = (saved_at or datetime.now(UTC)).astimezone(UTC)
    experiment_id = _experiment_id(clean_name, result.configuration_id)
    challenger = result.challenger_diagnostics
    production_metric = next(
        item
        for item in challenger.metrics
        if item.model_id == "elastic_net"
    )
    ordered_rmse = sorted(item.rmse for item in challenger.metrics)
    walk_forward = result.walk_forward_diagnostics
    lineage = result.factor_lineage
    panel_audit = result.panel_audit
    experiment = SavedExperiment(
        experiment_id=experiment_id,
        experiment_version=EXPERIMENT_VERSION,
        name=clean_name,
        saved_at=timestamp.isoformat(),
        configuration_id=result.configuration_id,
        permno=int(result.permno),
        ticker=result.ticker,
        company=result.company,
        as_of_date=result.as_of_date,
        snapshot_source=result.snapshot_source,
        replay_version=result.replay_version,
        target_month=result.target_month,
        benchmark_id=result.benchmark_id,
        benchmark_version=result.benchmark_version,
        benchmark_label=result.benchmark.label,
        benchmark_method=result.benchmark.method,
        selected_factors=tuple(result.selected_factors),
        training_window_months=result.training_window_months,
        interval_level=float(result.interval_level),
        expected_excess_return=float(result.expected_excess_return),
        probability_positive=float(result.probability_positive),
        interval_lower=float(result.interval_lower),
        interval_upper=float(result.interval_upper),
        model_reliability_score=float(
            result.reliability.model_reliability_score
        ),
        model_reliability_label=result.reliability.model_reliability_label,
        data_quality_score=float(result.reliability.data_quality_score),
        data_quality_label=result.reliability.data_quality_label,
        oos_r2_vs_zero=float(result.validation_metrics["oos_r2_vs_zero"]),
        interval_coverage=float(result.validation_metrics["interval_coverage"]),
        contributions=tuple(
            SavedContribution(
                factor_id=item.factor_id,
                contribution=float(item.contribution),
            )
            for item in result.contributions
        ),
        data_version=result.data_version,
        feature_version=result.feature_version,
        target_version=result.target_version,
        model_version=result.model_version,
        reliability_version=result.reliability_version,
        validation_version=result.validation_version,
        challenger_version=result.challenger_version,
        challenger_leader_model_id=challenger.leader_model_id,
        production_rmse=production_metric.rmse,
        production_rmse_rank=ordered_rmse.index(production_metric.rmse) + 1,
        walk_forward_version=result.walk_forward_version,
        walk_forward_rmse=walk_forward.rmse,
        walk_forward_oos_r2=walk_forward.oos_r2_vs_zero,
        walk_forward_directional_hit_rate=(
            walk_forward.directional_hit_rate
        ),
        walk_forward_interval_coverage=walk_forward.interval_coverage,
        walk_forward_mean_rank_ic=walk_forward.mean_rank_ic,
        lineage_version=result.lineage_version,
        factor_lineage_status=lineage.status,
        factor_freshness_score=lineage.freshness_score,
        stale_factor_count=lineage.stale_factor_count,
        aging_factor_count=lineage.aging_factor_count,
        research_proxy_factor_count=lineage.research_proxy_factor_count,
        audit_version=result.audit_version,
        panel_audit_id=panel_audit.audit_id,
        panel_audit_status=panel_audit.status,
        audit_blocking_issue_count=panel_audit.blocking_issue_count,
        audit_review_issue_count=panel_audit.review_issue_count,
    )
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    output_path = destination / f"{experiment_id}.json"
    temporary_path = output_path.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(experiment.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(output_path)
    return experiment, output_path


def list_experiments(output_dir: str | Path) -> tuple[SavedExperiment, ...]:
    directory = Path(output_dir).expanduser().resolve()
    if not directory.is_dir():
        return ()
    experiments = [
        _experiment_from_dict(
            json.loads(path.read_text(encoding="utf-8"))
        )
        for path in sorted(directory.glob("*.json"))
    ]
    return tuple(
        sorted(
            experiments,
            key=lambda item: (item.saved_at, item.name),
            reverse=True,
        )
    )


def comparison_warnings(
    experiments: tuple[SavedExperiment, ...],
) -> tuple[str, ...]:
    if len(experiments) < 2:
        return ()
    checks = (
        ("permno", "company/security"),
        ("as_of_date", "as-of date"),
        ("target_month", "target month"),
        ("benchmark_id", "benchmark"),
        ("benchmark_version", "benchmark-registry version"),
        ("training_window_months", "training window"),
        ("data_version", "data version"),
        ("model_version", "model version"),
        ("challenger_version", "challenger-suite version"),
        ("walk_forward_version", "walk-forward version"),
        ("lineage_version", "factor-lineage version"),
        ("audit_version", "panel-audit version"),
    )
    warnings = []
    for field, label in checks:
        values = {getattr(item, field) for item in experiments}
        if len(values) > 1:
            warnings.append(
                f"Selected experiments use different {label} values."
            )
    return tuple(warnings)


def comparison_records(
    experiments: tuple[SavedExperiment, ...],
) -> list[dict[str, object]]:
    if not experiments:
        return []
    baseline_return = experiments[0].expected_excess_return
    baseline_probability = experiments[0].probability_positive
    return [
        {
            "Experiment": comparison_label(item),
            "Ticker": item.ticker or "N/A",
            "Factors": len(item.selected_factors),
            "Factor set": ", ".join(item.selected_factors),
            "As-of mode": (
                "Historical replay"
                if item.snapshot_source == "historical_replay"
                else "Latest snapshot"
            ),
            "Training window": (
                "All available"
                if item.training_window_months is None
                else f"{item.training_window_months} months"
            ),
            "Benchmark": (
                getattr(item, "benchmark_label", None)
                or getattr(item, "benchmark_id", "Not recorded")
            ),
            "Expected excess return": item.expected_excess_return,
            "Expected-return delta vs first": (
                item.expected_excess_return - baseline_return
            ),
            "Probability positive": item.probability_positive,
            "Probability delta vs first": (
                item.probability_positive - baseline_probability
            ),
            "Interval width": item.interval_upper - item.interval_lower,
            "Model reliability": item.model_reliability_score,
            "Data quality": item.data_quality_score,
            "OOS R² vs zero": item.oos_r2_vs_zero,
            "Interval coverage": item.interval_coverage,
            "Best holdout model": item.challenger_leader_model_id or "Not recorded",
            "Production RMSE": item.production_rmse,
            "Production RMSE rank": item.production_rmse_rank,
            "Walk-forward RMSE": item.walk_forward_rmse,
            "Walk-forward OOS R²": item.walk_forward_oos_r2,
            "Walk-forward direction": (
                item.walk_forward_directional_hit_rate
            ),
            "Walk-forward coverage": (
                item.walk_forward_interval_coverage
            ),
            "Mean monthly rank IC": item.walk_forward_mean_rank_ic,
            "Factor lineage": (
                getattr(item, "factor_lineage_status", None)
                or "Not recorded"
            ),
            "Factor freshness": getattr(
                item, "factor_freshness_score", None
            ),
            "Stale factors": getattr(item, "stale_factor_count", None),
            "Aging factors": getattr(item, "aging_factor_count", None),
            "Research-lag factors": getattr(
                item, "research_proxy_factor_count", None
            ),
            "Panel audit": (
                getattr(item, "panel_audit_status", None)
                or "Not recorded"
            ),
            "Audit review items": getattr(
                item, "audit_review_issue_count", None
            ),
            "Run ID": item.configuration_id,
        }
        for item in experiments
    ]


def contribution_records(
    experiments: tuple[SavedExperiment, ...],
) -> list[dict[str, object]]:
    rows = []
    for experiment in experiments:
        for contribution in experiment.contributions:
            rows.append(
                {
                    "Experiment": comparison_label(experiment),
                    "Factor ID": contribution.factor_id,
                    "Contribution": contribution.contribution,
                }
            )
    return rows


def comparison_label(experiment: SavedExperiment) -> str:
    ticker = experiment.ticker or f"PERMNO {experiment.permno}"
    return (
        f"{experiment.name} · {ticker} · "
        f"{experiment.configuration_id[:6]}"
    )


def _validate_name(name: str) -> str:
    clean = " ".join(name.split())
    if not clean:
        raise ValueError("Experiment name is required.")
    if len(clean) > MAX_EXPERIMENT_NAME_LENGTH:
        raise ValueError(
            f"Experiment name must be {MAX_EXPERIMENT_NAME_LENGTH} characters or fewer."
        )
    return clean


def _experiment_id(name: str, configuration_id: str) -> str:
    payload = json.dumps(
        {"name": name, "configuration_id": configuration_id},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def _experiment_from_dict(payload: dict[str, object]) -> SavedExperiment:
    required_version = payload.get("experiment_version")
    if required_version not in SUPPORTED_EXPERIMENT_VERSIONS:
        raise ValueError(
            f"Unsupported experiment version: {required_version!r}."
        )
    return SavedExperiment(
        experiment_id=str(payload["experiment_id"]),
        experiment_version=str(payload["experiment_version"]),
        name=str(payload["name"]),
        saved_at=str(payload["saved_at"]),
        configuration_id=str(payload["configuration_id"]),
        permno=int(payload["permno"]),
        ticker=_optional_string(payload.get("ticker")),
        company=_optional_string(payload.get("company")),
        as_of_date=str(payload["as_of_date"]),
        snapshot_source=str(
            payload.get("snapshot_source", "latest_inference")
        ),
        replay_version=_optional_string(payload.get("replay_version")),
        target_month=str(payload["target_month"]),
        benchmark_id=str(payload["benchmark_id"]),
        benchmark_version=_optional_string(
            payload.get("benchmark_version")
        ),
        benchmark_label=_optional_string(payload.get("benchmark_label")),
        benchmark_method=_optional_string(payload.get("benchmark_method")),
        selected_factors=tuple(str(item) for item in payload["selected_factors"]),
        training_window_months=(
            None
            if payload.get("training_window_months") is None
            else int(payload["training_window_months"])
        ),
        interval_level=float(payload["interval_level"]),
        expected_excess_return=float(payload["expected_excess_return"]),
        probability_positive=float(payload["probability_positive"]),
        interval_lower=float(payload["interval_lower"]),
        interval_upper=float(payload["interval_upper"]),
        model_reliability_score=float(payload["model_reliability_score"]),
        model_reliability_label=str(payload["model_reliability_label"]),
        data_quality_score=float(payload["data_quality_score"]),
        data_quality_label=str(payload["data_quality_label"]),
        oos_r2_vs_zero=float(payload["oos_r2_vs_zero"]),
        interval_coverage=float(payload["interval_coverage"]),
        contributions=tuple(
            SavedContribution(
                factor_id=str(item["factor_id"]),
                contribution=float(item["contribution"]),
            )
            for item in payload["contributions"]
        ),
        data_version=str(payload["data_version"]),
        feature_version=str(payload["feature_version"]),
        target_version=str(payload["target_version"]),
        model_version=str(payload["model_version"]),
        reliability_version=str(payload["reliability_version"]),
        validation_version=str(payload["validation_version"]),
        challenger_version=_optional_string(
            payload.get("challenger_version")
        ),
        challenger_leader_model_id=_optional_string(
            payload.get("challenger_leader_model_id")
        ),
        production_rmse=(
            None
            if payload.get("production_rmse") is None
            else float(payload["production_rmse"])
        ),
        production_rmse_rank=(
            None
            if payload.get("production_rmse_rank") is None
            else int(payload["production_rmse_rank"])
        ),
        walk_forward_version=_optional_string(
            payload.get("walk_forward_version")
        ),
        walk_forward_rmse=_optional_float(
            payload.get("walk_forward_rmse")
        ),
        walk_forward_oos_r2=_optional_float(
            payload.get("walk_forward_oos_r2")
        ),
        walk_forward_directional_hit_rate=_optional_float(
            payload.get("walk_forward_directional_hit_rate")
        ),
        walk_forward_interval_coverage=_optional_float(
            payload.get("walk_forward_interval_coverage")
        ),
        walk_forward_mean_rank_ic=_optional_float(
            payload.get("walk_forward_mean_rank_ic")
        ),
        lineage_version=_optional_string(payload.get("lineage_version")),
        factor_lineage_status=_optional_string(
            payload.get("factor_lineage_status")
        ),
        factor_freshness_score=_optional_float(
            payload.get("factor_freshness_score")
        ),
        stale_factor_count=_optional_int(payload.get("stale_factor_count")),
        aging_factor_count=_optional_int(payload.get("aging_factor_count")),
        research_proxy_factor_count=_optional_int(
            payload.get("research_proxy_factor_count")
        ),
        audit_version=_optional_string(payload.get("audit_version")),
        panel_audit_id=_optional_string(payload.get("panel_audit_id")),
        panel_audit_status=_optional_string(
            payload.get("panel_audit_status")
        ),
        audit_blocking_issue_count=_optional_int(
            payload.get("audit_blocking_issue_count")
        ),
        audit_review_issue_count=_optional_int(
            payload.get("audit_review_issue_count")
        ),
    )


def _optional_string(value: object) -> str | None:
    return None if value is None else str(value)


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)
