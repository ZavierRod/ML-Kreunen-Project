"""Immutable forecast-run artifacts and content-aware local caching."""

from __future__ import annotations

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

import pandas as pd

from .model import (
    ForecastRequest,
    ForecastResult,
    forecast_configuration_id,
    generate_forecast,
    runtime_versions,
)

RUN_ARTIFACT_VERSION = "forecast-run-v1"
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

    result = generate_forecast(training_panel, inference_panel, request)
    if result.configuration_id != configuration_id:
        raise RuntimeError(
            "Preflight configuration ID does not match the fitted forecast."
        )
    if lookup.execution is not None:
        cached_result = lookup.execution.result
        if not _results_equivalent(
            cached_result.to_dict(),
            result.to_dict(),
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
            "replay_version": result.replay_version,
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
    except (KeyError, TypeError, ValueError):
        return _CacheLookup(None, "artifact result is invalid")
    if not created_by:
        return _CacheLookup(None, "artifact creator is invalid")
    if result.configuration_id != expected_configuration_id:
        return _CacheLookup(None, "result configuration ID does not match")
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
