"""Versioned data-contract audit for forecast training and inference panels."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from pandas.tseries.offsets import MonthEnd

from .features import FUNDAMENTAL_FACTOR_IDS

AUDIT_VERSION = "panel-audit-v4"
OUTCOME_COLUMNS = (
    "stock_return_next_month",
    "benchmark_return",
    "excess_return_next_month",
)
DELISTING_COLUMNS = ("dlret", "delisting_return", "dlstcd")
DELISTING_INTEGRATION_COLUMNS = (
    "delisting_return_included",
    "return_includes_delisting",
)


@dataclass(frozen=True)
class AuditCheck:
    check_id: str
    label: str
    status: str
    severity: str
    observed: str
    detail: str


@dataclass(frozen=True)
class PanelAudit:
    version: str
    audit_id: str
    scope_content_sha256: str
    status: str
    as_of_date: str
    benchmark_id: str
    selected_factors: tuple[str, ...]
    historical_rows: int
    historical_months: int
    inference_rows: int
    blocking_issue_count: int
    review_issue_count: int
    extreme_stock_return_count: int
    checks: tuple[AuditCheck, ...]


def audit_forecast_panels(
    historical: pd.DataFrame,
    inference: pd.DataFrame,
    *,
    as_of_date: str | pd.Timestamp,
    benchmark_id: str,
    selected_factors: tuple[str, ...],
    strict: bool = True,
) -> PanelAudit:
    """Audit the exact panel scope used by a forecast."""
    as_of = _month_end(as_of_date)
    checks: list[AuditCheck] = []
    required_historical = {
        "permno",
        "month_end",
        "target_month",
        "benchmark_id",
        *OUTCOME_COLUMNS,
    }
    required_inference = {
        "permno",
        "month_end",
        "target_month",
        "benchmark_id",
        *OUTCOME_COLUMNS,
    }
    missing_historical = sorted(
        required_historical - set(historical.columns)
    )
    missing_inference = sorted(required_inference - set(inference.columns))
    checks.append(
        _binary_check(
            "required_columns",
            "Required audit columns",
            not missing_historical and not missing_inference,
            (
                "all required columns present"
                if not missing_historical and not missing_inference
                else "missing training: "
                + ", ".join(missing_historical or ("none",))
                + "; missing inference: "
                + ", ".join(missing_inference or ("none",))
            ),
            "Training and inference must preserve return and benchmark fields "
            "needed to verify the target contract.",
        )
    )
    if missing_historical or missing_inference:
        return _finish_audit(
            checks,
            as_of,
            benchmark_id,
            historical,
            inference,
            selected_factors=selected_factors,
            extreme_count=0,
            strict=strict,
        )

    historical_months = _months(historical["month_end"])
    historical_targets = _months(historical["target_month"])
    inference_months = _months(inference["month_end"])
    inference_targets = _months(inference["target_month"])

    duplicate_count = int(
        historical.duplicated(["permno", "month_end"]).sum()
        + inference.duplicated(["permno", "month_end"]).sum()
    )
    checks.append(
        _binary_check(
            "unique_security_month",
            "Unique security-month rows",
            duplicate_count == 0,
            f"{duplicate_count} duplicate rows",
            "Each permanent security ID may appear once per panel month.",
        )
    )
    future_training = int((historical_months >= as_of).sum())
    checks.append(
        _binary_check(
            "historical_cutoff",
            "Historical cutoff",
            future_training == 0,
            f"{future_training} rows on or after as-of",
            "All fitted outcomes must precede the forecast as-of month.",
        )
    )
    bad_target_months = int(
        (historical_targets != historical_months + MonthEnd(1)).sum()
        + (inference_targets != inference_months + MonthEnd(1)).sum()
    )
    checks.append(
        _binary_check(
            "calendar_target",
            "Exact next-calendar-month target",
            bad_target_months == 0,
            f"{bad_target_months} non-contiguous target rows",
            "Every target month must be exactly one calendar month after its "
            "factor observation.",
        )
    )

    target_values = historical["excess_return_next_month"].to_numpy(
        dtype=float
    )
    stock_values = historical["stock_return_next_month"].to_numpy(
        dtype=float
    )
    benchmark_values = historical["benchmark_return"].to_numpy(dtype=float)
    finite = (
        np.isfinite(target_values)
        & np.isfinite(stock_values)
        & np.isfinite(benchmark_values)
    )
    nonfinite_count = int((~finite).sum())
    checks.append(
        _binary_check(
            "finite_training_outcomes",
            "Finite training outcomes",
            nonfinite_count == 0,
            f"{nonfinite_count} non-finite rows",
            "Training stock, benchmark, and excess returns must be finite.",
        )
    )
    mismatch_count = int(
        (
            finite
            & ~np.isclose(
                target_values,
                stock_values - benchmark_values,
                rtol=1e-10,
                atol=1e-12,
            )
        ).sum()
    )
    checks.append(
        _binary_check(
            "target_reconciliation",
            "Excess-return reconciliation",
            mismatch_count == 0,
            f"{mismatch_count} unreconciled labels",
            "Excess return must equal stock return minus benchmark return.",
        )
    )

    benchmark_values_seen = set(
        historical["benchmark_id"].dropna().astype(str)
    ) | set(inference["benchmark_id"].dropna().astype(str))
    benchmark_matches = benchmark_values_seen == {benchmark_id}
    checks.append(
        _binary_check(
            "benchmark_identity",
            "Benchmark identity",
            benchmark_matches,
            ", ".join(sorted(benchmark_values_seen)) or "none",
            "Training and inference must use the requested benchmark only.",
        )
    )

    leaked_count = int(
        sum(inference[column].notna().sum() for column in OUTCOME_COLUMNS)
    )
    checks.append(
        _binary_check(
            "inference_outcome_leakage",
            "Inference outcome isolation",
            leaked_count == 0,
            f"{leaked_count} populated outcome cells",
            "Inference rows must not expose realized stock, benchmark, or "
            "excess-return outcomes.",
        )
    )

    missing_source_dates, source_date_violations = _source_date_issues(
        historical,
        inference,
        selected_factors,
    )
    checks.append(
        _binary_check(
            "source_date_completeness",
            "Source-date completeness",
            missing_source_dates == 0,
            f"{missing_source_dates} selected-factor rows missing source dates",
            "Rows with a selected factor value must preserve the market or "
            "fundamental dates needed for point-in-time review.",
        )
    )
    checks.append(
        _binary_check(
            "source_date_cutoff",
            "Source-date cutoff",
            source_date_violations == 0,
            f"{source_date_violations} future-dated source rows",
            "Market and available fundamental source dates may not exceed "
            "their factor observation month.",
        )
    )

    extreme_count = int((np.abs(stock_values[finite]) > 1.0).sum())
    checks.append(
        _review_check(
            "extreme_stock_returns",
            "Extreme stock-return review",
            extreme_count > 0,
            f"{extreme_count} rows above 100% absolute return",
            "Extreme observations remain in the research panel and require "
            "corporate-action or source review before institutional use.",
        )
    )
    has_delisting_fields = any(
        column in historical.columns for column in DELISTING_COLUMNS
    )
    integration_columns = [
        column
        for column in DELISTING_INTEGRATION_COLUMNS
        if column in historical
    ]
    delisting_integrated = bool(
        integration_columns
        and historical[integration_columns]
        .fillna(False)
        .astype(bool)
        .all(axis=None)
    )
    checks.append(
        _review_check(
            "delisting_coverage",
            "Delisting-return coverage",
            not delisting_integrated,
            (
                "integration marker verified"
                if delisting_integrated
                else "source field present; integration not proven"
                if has_delisting_fields
                else "explicit delisting field unavailable"
            ),
            "A source field alone is insufficient; the return pipeline must "
            "preserve an explicit marker proving delisting-return integration.",
        )
    )
    uses_fundamentals = bool(
        set(selected_factors) & set(FUNDAMENTAL_FACTOR_IDS)
    )
    checks.append(
        _review_check(
            "fundamental_availability",
            "Fundamental availability",
            uses_fundamentals,
            (
                "fixed-lag research proxy in use"
                if uses_fundamentals
                else "no selected fundamental factors"
            ),
            "Selected fundamentals use the documented fixed-lag proxy until "
            "actual filing or announcement timestamps are available.",
        )
    )
    return _finish_audit(
        checks,
        as_of,
        benchmark_id,
        historical,
        inference,
        selected_factors=selected_factors,
        extreme_count=extreme_count,
        strict=strict,
    )


def _finish_audit(
    checks: list[AuditCheck],
    as_of: pd.Timestamp,
    benchmark_id: str,
    historical: pd.DataFrame,
    inference: pd.DataFrame,
    *,
    selected_factors: tuple[str, ...],
    extreme_count: int,
    strict: bool,
) -> PanelAudit:
    blocking_count = sum(check.status == "Block" for check in checks)
    review_count = sum(check.status == "Review" for check in checks)
    status = (
        "Blocked"
        if blocking_count
        else "Review required"
        if review_count
        else "Passed"
    )
    scope_content_sha256 = _scope_content_sha256(
        historical,
        inference,
        selected_factors,
    )
    payload = {
        "version": AUDIT_VERSION,
        "as_of_date": as_of.date().isoformat(),
        "benchmark_id": benchmark_id,
        "selected_factors": list(selected_factors),
        "scope_content_sha256": scope_content_sha256,
        "historical_rows": len(historical),
        "inference_rows": len(inference),
        "checks": [asdict(check) for check in checks],
    }
    audit_id = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    assessment = PanelAudit(
        version=AUDIT_VERSION,
        audit_id=audit_id,
        scope_content_sha256=scope_content_sha256,
        status=status,
        as_of_date=as_of.date().isoformat(),
        benchmark_id=benchmark_id,
        selected_factors=selected_factors,
        historical_rows=int(len(historical)),
        historical_months=(
            int(pd.to_datetime(historical["month_end"]).nunique())
            if "month_end" in historical
            else 0
        ),
        inference_rows=int(len(inference)),
        blocking_issue_count=blocking_count,
        review_issue_count=review_count,
        extreme_stock_return_count=extreme_count,
        checks=tuple(checks),
    )
    if strict and blocking_count:
        failures = "; ".join(
            f"{check.label}: {check.observed}"
            for check in checks
            if check.status == "Block"
        )
        raise ValueError(f"Forecast panel audit failed: {failures}")
    return assessment


def _binary_check(
    check_id: str,
    label: str,
    passed: bool,
    observed: str,
    detail: str,
) -> AuditCheck:
    return AuditCheck(
        check_id=check_id,
        label=label,
        status="Pass" if passed else "Block",
        severity="blocking",
        observed=observed,
        detail=detail,
    )


def _review_check(
    check_id: str,
    label: str,
    needs_review: bool,
    observed: str,
    detail: str,
) -> AuditCheck:
    return AuditCheck(
        check_id=check_id,
        label=label,
        status="Review" if needs_review else "Pass",
        severity="review",
        observed=observed,
        detail=detail,
    )


def _months(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values, errors="coerce")
    return parsed.dt.to_period("M").dt.to_timestamp("M")


def _month_end(value: object) -> pd.Timestamp:
    return pd.Timestamp(value).to_period("M").to_timestamp("M")


def _source_date_issues(
    historical: pd.DataFrame,
    inference: pd.DataFrame,
    selected_factors: tuple[str, ...],
) -> tuple[int, int]:
    fundamental_factors = tuple(
        factor
        for factor in selected_factors
        if factor in FUNDAMENTAL_FACTOR_IDS
    )
    market_factors = tuple(
        factor
        for factor in selected_factors
        if factor not in FUNDAMENTAL_FACTOR_IDS
    )
    missing = 0
    violations = 0
    for frame in (historical, inference):
        month = _months(frame["month_end"])
        groups = (
            (market_factors, ("source_last_trading_date",)),
            (
                fundamental_factors,
                ("datadate", "fund_available_date"),
            ),
        )
        for factors, date_columns in groups:
            if not factors:
                continue
            available_factors = [
                factor for factor in factors if factor in frame
            ]
            has_value = (
                frame[available_factors].notna().any(axis=1)
                if available_factors
                else pd.Series(False, index=frame.index)
            )
            for column in date_columns:
                if column not in frame:
                    missing += int(has_value.sum())
                    continue
                raw = frame[column]
                source = pd.to_datetime(raw, errors="coerce")
                missing += int(
                    (has_value & (raw.isna() | source.isna())).sum()
                )
                violations += int(
                    (has_value & source.notna() & (source > month)).sum()
                )
    return missing, violations


def _scope_content_sha256(
    historical: pd.DataFrame,
    inference: pd.DataFrame,
    selected_factors: tuple[str, ...],
) -> str:
    columns = tuple(
        dict.fromkeys(
            (
                "permno",
                "month_end",
                "target_month",
                "benchmark_id",
                *OUTCOME_COLUMNS,
                "source_last_trading_date",
                "datadate",
                "fund_available_date",
                *selected_factors,
                *DELISTING_COLUMNS,
                *DELISTING_INTEGRATION_COLUMNS,
            )
        )
    )
    digest = hashlib.sha256()
    for frame in (historical, inference):
        available = [
            column for column in columns if column in frame.columns
        ]
        hashed = pd.util.hash_pandas_object(
            frame[available],
            index=False,
            categorize=True,
        )
        digest.update(
            hashed.to_numpy(dtype=np.uint64, copy=False).tobytes()
        )
    return digest.hexdigest()
