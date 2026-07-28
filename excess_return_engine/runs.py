"""Immutable forecast-run artifacts and content-aware local caching."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import types
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime, timezone
from numbers import Real
from pathlib import Path
from typing import Any, TypeVar, Union, get_args, get_origin, get_type_hints

import numpy as np
import pandas as pd

from .model import (
    ForecastRequest,
    ForecastResult,
    forecast_configuration_id,
    generate_forecast_computation,
    runtime_versions,
)

RUN_ARTIFACT_VERSION = "forecast-run-v2"
RUN_EVENT_VERSION = "forecast-run-event-v1"


@dataclass(frozen=True)
class ForecastExecution:
    result: ForecastResult
    cache_status: str
    cache_reason: str
    artifact_path: Path
    created_at_utc: str
    actor: str
    created_by: str
    runtime_versions: dict[str, str]
    walk_forward_path: Path
    walk_forward_rows: int
    walk_forward_sha256: str


@dataclass(frozen=True)
class _CacheLookup:
    execution: ForecastExecution | None
    reason: str


def execute_forecast(
    training_panel: pd.DataFrame,
    inference_panel: pd.DataFrame,
    request: ForecastRequest,
    output_dir: str | Path,
    *,
    force_refresh: bool = False,
) -> ForecastExecution:
    """Load an identical immutable run or fit and atomically persist a new one."""
    configuration_id = forecast_configuration_id(
        training_panel,
        inference_panel,
        request,
    )
    resolved_as_of = (
        pd.Timestamp(request.as_of_date)
        if request.as_of_date is not None
        else pd.to_datetime(inference_panel["month_end"]).max()
    ).to_period("M").to_timestamp("M").date().isoformat()
    request_payload = _request_payload(request, resolved_as_of)
    destination = Path(output_dir).expanduser().resolve()
    artifact_path = destination / f"{configuration_id}.json"
    actor = _current_actor()
    artifact_existed = artifact_path.is_file()
    lookup = _load_cached_execution(
        artifact_path,
        request_payload,
        configuration_id,
        actor,
    )
    if lookup.execution is not None and not force_refresh:
        return _record_execution_event(
            destination,
            lookup.execution,
            request_payload,
        )

    computation = generate_forecast_computation(
        training_panel,
        inference_panel,
        request,
    )
    result = computation.result
    if result.configuration_id != configuration_id:
        raise RuntimeError(
            "Preflight configuration ID does not match the fitted forecast."
        )
    walk_forward_predictions = computation.walk_forward_predictions.copy()
    walk_forward_predictions.insert(
        0,
        "configuration_id",
        configuration_id,
    )
    _validate_prediction_ledger(
        walk_forward_predictions,
        result,
    )
    walk_forward_sha256 = _prediction_content_sha256(
        walk_forward_predictions
    )
    walk_forward_path = (
        destination / f"{configuration_id}.walk_forward.parquet"
    )
    if lookup.execution is not None:
        cached_result = lookup.execution.result
        if not _results_equivalent(
            cached_result.to_dict(),
            result.to_dict(),
        ) or (
            lookup.execution.walk_forward_sha256
            != walk_forward_sha256
        ):
            raise RuntimeError(
                "Recomputed result differs from its immutable cached run."
            )
        verified = ForecastExecution(
            result=cached_result,
            cache_status="verified",
            cache_reason="recomputation matched the immutable cached run",
            artifact_path=artifact_path,
            created_at_utc=lookup.execution.created_at_utc,
            actor=actor,
            created_by=lookup.execution.created_by,
            runtime_versions=lookup.execution.runtime_versions,
            walk_forward_path=lookup.execution.walk_forward_path,
            walk_forward_rows=lookup.execution.walk_forward_rows,
            walk_forward_sha256=(
                lookup.execution.walk_forward_sha256
            ),
        )
        return _record_execution_event(
            destination,
            verified,
            request_payload,
        )
    if force_refresh and artifact_existed:
        cache_status = "repaired"
        cache_reason = lookup.reason
    elif force_refresh:
        cache_status = "generated"
        cache_reason = "no artifact existed to verify"
    elif artifact_existed:
        cache_status = "repaired"
        cache_reason = lookup.reason
    else:
        cache_status = "generated"
        cache_reason = lookup.reason
    if artifact_path.is_file() and not artifact_existed:
        raise RuntimeError(
            "Forecast artifact appeared while the run was being generated."
        )
    created_at = datetime.now(timezone.utc).isoformat()
    versions = runtime_versions()
    _atomic_parquet_write(
        walk_forward_path,
        walk_forward_predictions,
    )
    payload = {
        "run_artifact_version": RUN_ARTIFACT_VERSION,
        "created_at_utc": created_at,
        "created_by": actor,
        "configuration_id": configuration_id,
        "request": request_payload,
        "runtime_versions": versions,
        "source_versions": {
            "data_version": result.data_version,
            "feature_version": result.feature_version,
            "target_version": result.target_version,
            "model_version": result.model_version,
            "challenger_version": result.challenger_version,
            "reliability_version": result.reliability_version,
            "validation_version": result.validation_version,
            "walk_forward_version": result.walk_forward_version,
            "lineage_version": result.lineage_version,
            "audit_version": result.audit_version,
            "replay_version": result.replay_version,
        },
        "walk_forward_predictions": {
            "artifact": walk_forward_path.name,
            "rows": int(len(walk_forward_predictions)),
            "content_sha256": walk_forward_sha256,
        },
        "result": result.to_dict(),
    }
    _atomic_json_write(artifact_path, payload)
    execution = ForecastExecution(
        result=result,
        cache_status=cache_status,
        cache_reason=cache_reason,
        artifact_path=artifact_path,
        created_at_utc=created_at,
        actor=actor,
        created_by=actor,
        runtime_versions=versions,
        walk_forward_path=walk_forward_path,
        walk_forward_rows=int(len(walk_forward_predictions)),
        walk_forward_sha256=walk_forward_sha256,
    )
    return _record_execution_event(
        destination,
        execution,
        request_payload,
    )


def _load_cached_execution(
    artifact_path: Path,
    expected_request: dict[str, object],
    expected_configuration_id: str,
    actor: str,
) -> _CacheLookup:
    if not artifact_path.is_file():
        return _CacheLookup(None, "artifact not found")
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _CacheLookup(None, "artifact is unreadable")
    if not isinstance(payload, dict):
        return _CacheLookup(None, "artifact root is not an object")
    if payload.get("run_artifact_version") != RUN_ARTIFACT_VERSION:
        return _CacheLookup(None, "artifact version is stale")
    if payload.get("configuration_id") != expected_configuration_id:
        return _CacheLookup(None, "configuration ID does not match")
    if payload.get("request") != expected_request:
        return _CacheLookup(None, "forecast request does not match")
    versions = payload.get("runtime_versions")
    if versions != runtime_versions():
        return _CacheLookup(None, "numerical runtime versions changed")
    try:
        result_payload = payload["result"]
        result = _dataclass_from_dict(ForecastResult, result_payload)
        created_at = str(payload["created_at_utc"])
        created_by = str(payload["created_by"]).strip()
        walk_forward_metadata = payload["walk_forward_predictions"]
        if not isinstance(walk_forward_metadata, dict):
            raise TypeError("Walk-forward metadata must be an object.")
        walk_forward_name = str(walk_forward_metadata["artifact"])
        expected_name = (
            f"{expected_configuration_id}.walk_forward.parquet"
        )
        if walk_forward_name != expected_name:
            raise ValueError("Walk-forward artifact name does not match.")
        walk_forward_path = artifact_path.parent / walk_forward_name
        walk_forward_rows = int(walk_forward_metadata["rows"])
        walk_forward_sha256 = str(
            walk_forward_metadata["content_sha256"]
        )
        walk_forward_predictions = pd.read_parquet(walk_forward_path)
        _validate_prediction_ledger(
            walk_forward_predictions,
            result,
        )
    except (KeyError, TypeError, ValueError):
        return _CacheLookup(None, "artifact result is invalid")
    except (OSError, FileNotFoundError):
        return _CacheLookup(None, "walk-forward artifact is unreadable")
    if not created_by:
        return _CacheLookup(None, "artifact creator is invalid")
    if result.configuration_id != expected_configuration_id:
        return _CacheLookup(None, "result configuration ID does not match")
    if len(walk_forward_predictions) != walk_forward_rows:
        return _CacheLookup(None, "walk-forward row count does not match")
    if (
        _prediction_content_sha256(walk_forward_predictions)
        != walk_forward_sha256
    ):
        return _CacheLookup(None, "walk-forward content hash does not match")
    return _CacheLookup(
        ForecastExecution(
            result=result,
            cache_status="cached",
            cache_reason="identical immutable run found",
            artifact_path=artifact_path,
            created_at_utc=created_at,
            actor=actor,
            created_by=created_by,
            runtime_versions=dict(versions),
            walk_forward_path=walk_forward_path,
            walk_forward_rows=walk_forward_rows,
            walk_forward_sha256=walk_forward_sha256,
        ),
        "identical immutable run found",
    )


def _atomic_json_write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.stem}-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = handle.name
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and os.path.exists(temporary_path):
            os.unlink(temporary_path)


def _atomic_parquet_write(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.stem}-",
            suffix=".parquet.tmp",
            delete=False,
        ) as handle:
            temporary_path = handle.name
        frame.to_parquet(temporary_path, index=False)
        descriptor = os.open(temporary_path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and os.path.exists(temporary_path):
            os.unlink(temporary_path)


def _prediction_content_sha256(frame: pd.DataFrame) -> str:
    canonical = frame.copy()
    date_columns = ("as_of_date", "target_month", "training_end")
    for column in date_columns:
        canonical[column] = (
            pd.to_datetime(canonical[column])
            .dt.strftime("%Y-%m-%d")
            .fillna("")
        )
    canonical["configuration_id"] = canonical[
        "configuration_id"
    ].astype(str)
    canonical["split"] = canonical["split"].astype(str)
    canonical["permno"] = canonical["permno"].astype(np.int64)
    canonical["training_rows"] = (
        pd.to_numeric(canonical["training_rows"], errors="coerce")
        .fillna(-1)
        .astype(np.int64)
    )
    numeric_columns = tuple(
        column
        for column in canonical.columns
        if column
        not in {
            "configuration_id",
            "split",
            "as_of_date",
            "target_month",
            "training_end",
            "permno",
            "training_rows",
        }
    )
    canonical[list(numeric_columns)] = canonical[
        list(numeric_columns)
    ].astype(np.float64)
    digest = hashlib.sha256()
    digest.update(
        json.dumps(
            list(canonical.columns),
            separators=(",", ":"),
        ).encode()
    )
    digest.update(
        pd.util.hash_pandas_object(
            canonical,
            index=False,
            categorize=True,
        ).to_numpy(dtype=np.uint64, copy=False).tobytes()
    )
    return digest.hexdigest()


def _validate_prediction_ledger(
    frame: pd.DataFrame,
    result: ForecastResult,
) -> None:
    required = {
        "configuration_id",
        "permno",
        "as_of_date",
        "target_month",
        "actual_excess_return",
        "predicted_excess_return",
        "residual",
        "probability_positive",
        "interval_lower",
        "interval_upper",
        "interval_level",
        "split",
        "training_end",
        "training_rows",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(
            "Walk-forward ledger is missing columns: "
            + ", ".join(missing)
        )
    if frame.empty:
        raise ValueError("Walk-forward ledger is empty.")
    if frame.duplicated(
        ["configuration_id", "permno", "as_of_date", "split"]
    ).any():
        raise ValueError(
            "Walk-forward ledger has duplicate security-month rows."
        )
    if set(frame["configuration_id"].astype(str)) != {
        result.configuration_id
    }:
        raise ValueError("Walk-forward ledger has the wrong run ID.")
    as_of = pd.to_datetime(frame["as_of_date"])
    target = pd.to_datetime(frame["target_month"])
    training_end = pd.to_datetime(frame["training_end"])
    if not (target == as_of + pd.offsets.MonthEnd(1)).all():
        raise ValueError(
            "Walk-forward ledger target is not the exact next month."
        )
    if training_end.isna().any() or not (training_end < as_of).all():
        raise ValueError(
            "Walk-forward ledger training cutoff is not before prediction."
        )
    if (
        pd.to_numeric(frame["training_rows"], errors="coerce").isna().any()
        or (pd.to_numeric(frame["training_rows"]) <= 0).any()
    ):
        raise ValueError(
            "Walk-forward ledger training row counts are invalid."
        )
    split = frame["split"].astype(str)
    if set(split) != {
        "calibration_residual",
        "walk_forward_evaluation",
    }:
        raise ValueError("Walk-forward ledger has unexpected split labels.")
    diagnostics = result.walk_forward_diagnostics
    calibration_count = int((split == "calibration_residual").sum())
    evaluation_count = int(
        (split == "walk_forward_evaluation").sum()
    )
    if calibration_count != diagnostics.calibration_residual_rows:
        raise ValueError(
            "Walk-forward calibration row count does not match diagnostics."
        )
    if evaluation_count != diagnostics.evaluation_rows:
        raise ValueError(
            "Walk-forward evaluation row count does not match diagnostics."
        )
    evaluation = frame[split == "walk_forward_evaluation"]
    if int(evaluation["as_of_date"].nunique()) != (
        diagnostics.evaluation_months
    ):
        raise ValueError(
            "Walk-forward month count does not match diagnostics."
        )
    evaluation_as_of = pd.to_datetime(evaluation["as_of_date"])
    if (
        evaluation_as_of.min().date().isoformat()
        != diagnostics.evaluation_start
        or evaluation_as_of.max().date().isoformat()
        != diagnostics.evaluation_end
    ):
        raise ValueError(
            "Walk-forward date range does not match diagnostics."
        )
    actual = frame["actual_excess_return"].to_numpy(dtype=float)
    predicted = frame["predicted_excess_return"].to_numpy(dtype=float)
    residual = frame["residual"].to_numpy(dtype=float)
    if not np.allclose(
        actual - predicted,
        residual,
        rtol=1e-10,
        atol=1e-12,
    ):
        raise ValueError("Walk-forward residuals do not reconcile.")
    if not evaluation["probability_positive"].between(0, 1).all():
        raise ValueError(
            "Walk-forward probabilities are outside the unit interval."
        )
    if not (
        evaluation["interval_lower"] <= evaluation["interval_upper"]
    ).all():
        raise ValueError("Walk-forward intervals are inverted.")
    if not np.allclose(
        evaluation["interval_level"].to_numpy(dtype=float),
        result.interval_level,
    ):
        raise ValueError(
            "Walk-forward interval level does not match the forecast."
        )


def _current_actor() -> str:
    actor = os.getenv("FORECAST_RUN_ACTOR", "local-research-user").strip()
    return actor or "local-research-user"


def _record_execution_event(
    destination: Path,
    execution: ForecastExecution,
    request_payload: dict[str, object],
) -> ForecastExecution:
    event = {
        "run_event_version": RUN_EVENT_VERSION,
        "occurred_at_utc": datetime.now(timezone.utc).isoformat(),
        "actor": execution.actor,
        "configuration_id": execution.result.configuration_id,
        "cache_status": execution.cache_status,
        "cache_reason": execution.cache_reason,
        "artifact": execution.artifact_path.name,
        "walk_forward_artifact": execution.walk_forward_path.name,
        "walk_forward_rows": execution.walk_forward_rows,
        "request": request_payload,
    }
    destination.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    descriptor = os.open(
        destination / "forecast_run_events.jsonl",
        os.O_APPEND | os.O_CREAT | os.O_WRONLY,
        0o600,
    )
    try:
        remaining = memoryview(encoded)
        while remaining:
            written = os.write(descriptor, remaining)
            if written == 0:
                raise OSError("Could not append forecast run event.")
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return execution


def _json_value(value: object) -> object:
    return json.loads(json.dumps(value, sort_keys=True))


def _request_payload(
    request: ForecastRequest,
    resolved_as_of: str,
) -> dict[str, object]:
    payload = _json_value(asdict(request))
    if not isinstance(payload, dict):  # pragma: no cover - asdict contract.
        raise TypeError("Forecast request did not serialize to an object.")
    payload["as_of_date"] = resolved_as_of
    return payload


def _results_equivalent(first: object, second: object) -> bool:
    if isinstance(first, dict) and isinstance(second, dict):
        return first.keys() == second.keys() and all(
            _results_equivalent(first[key], second[key]) for key in first
        )
    if isinstance(first, (list, tuple)) and isinstance(second, (list, tuple)):
        return len(first) == len(second) and all(
            _results_equivalent(left, right)
            for left, right in zip(first, second)
        )
    if (
        isinstance(first, Real)
        and not isinstance(first, bool)
        and isinstance(second, Real)
        and not isinstance(second, bool)
    ):
        if math.isnan(float(first)) and math.isnan(float(second)):
            return True
        return math.isclose(
            float(first),
            float(second),
            rel_tol=1e-10,
            abs_tol=1e-12,
        )
    return first == second


T = TypeVar("T")


def _dataclass_from_dict(data_type: type[T], payload: object) -> T:
    if not is_dataclass(data_type) or not isinstance(payload, dict):
        raise TypeError("Expected a dataclass type and object payload.")
    hints = get_type_hints(data_type)
    values = {}
    for field in fields(data_type):
        if field.name not in payload:
            raise ValueError(f"Missing field: {field.name}")
        values[field.name] = _decode_value(
            hints[field.name],
            payload[field.name],
        )
    return data_type(**values)


def _decode_value(data_type: object, value: object) -> object:
    if data_type is Any:
        return value
    if value is None:
        if type(None) in get_args(data_type):
            return None
        raise TypeError("Unexpected null value.")
    if isinstance(data_type, type) and is_dataclass(data_type):
        return _dataclass_from_dict(data_type, value)

    origin = get_origin(data_type)
    arguments = get_args(data_type)
    if origin is tuple:
        if not isinstance(value, list):
            raise TypeError("Expected an array for a tuple field.")
        item_type = arguments[0]
        return tuple(_decode_value(item_type, item) for item in value)
    if origin is list:
        if not isinstance(value, list):
            raise TypeError("Expected an array for a list field.")
        return [_decode_value(arguments[0], item) for item in value]
    if origin is dict:
        if not isinstance(value, dict):
            raise TypeError("Expected an object for a dictionary field.")
        key_type, item_type = arguments
        return {
            _decode_value(key_type, key): _decode_value(item_type, item)
            for key, item in value.items()
        }
    if origin in {Union, types.UnionType}:
        for candidate in arguments:
            if isinstance(candidate, type) and type(value) is candidate:
                return value
        for candidate in arguments:
            if candidate is type(None):
                continue
            try:
                return _decode_value(candidate, value)
            except (TypeError, ValueError):
                continue
        raise TypeError("Value does not match a union field.")
    if data_type in {str, int, float, bool}:
        if type(value) is data_type:
            return value
        return data_type(value)
    return value
