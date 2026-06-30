#!/usr/bin/env python3
"""Build the Phase 7 FCF factor decomposition and six-factor analysis.

Phase 7 mirrors the EPS work (Phases 1-4) but for Free Cash Flow per share.

It builds two FCF identities that tie out exactly:

    FCF/Share = Rev/Share x FCF Margin                (two-factor)
    FCF/Share = Revenue x FCF Margin / Shares         (three-factor)

For each adjacent year-over-year period in the requested windows, this script:

1. Rebuilds the annual driver table from `Model.csv` (adds Free Cash Flow)
2. Builds the exact two-factor FCF bridge (Rev/S + FCF Margin)
3. Builds the exact three-factor FCF bridge (Revenue + FCF Margin - Shares)
4. Ranks the three factors by contribution magnitude
5. Adds absolute-contribution-share weights (|c_i| / sum |c_j|)
6. Joins the Phase 3 EPS decomposition to produce a combined six-factor panel
7. Writes explicit validation outputs so the phase is test-backed
8. Writes a Sheet1-style factor block and a narrative summary

The log-form contribution method is used because it ties out exactly:

    log(FCF/S_t / FCF/S_t-1)
    = log(Revenue_t / Revenue_t-1)
    + log(FCF_margin_t / FCF_margin_t-1)
    - log(Shares_t / Shares_t-1)

Outputs (in outputs/phase7/):

- `phase7_fcf_annual_tables.csv`
- `phase7_fcf_two_factor_yoy.csv`
- `phase7_fcf_three_factor_decomposition.csv`
- `phase7_combined_six_factor_panel.csv`
- `phase7_fcf_validation_results.csv`
- `phase7_fcf_factors_sheet_style.csv`
- `phase7_fcf_summary.md`
"""

from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "data" / "GOOG MS ML 10-Year Actuals" / "Model.csv"
PHASE3_DECOMP_PATH = (
    ROOT / "outputs" / "phase3" / "phase3_eps_three_factor_decomposition.csv"
)

KEY_ROWS = {
    "revenue": "Total Gross revenue (GAAP)",
    "net_income": "Net income, reported",
    "shares": "Average diluted shares",
    "free_cash_flow": "Free cash flow",
}

WINDOWS: List[Tuple[str, int, int]] = [
    ("2015_2025", 2015, 2025),
    ("2010_2025", 2010, 2025),
    ("2001_2025", 2001, 2025),
]

# Sheet1-style replication block (formulas sheet covered Years 1-5: 2015-2020).
SHEET_START_YEAR = 2015
SHEET_END_YEAR = 2020

# Rolling-five-year analysis uses the most recent calendar years.
ROLLING_WINDOW_LABEL = "2015_2025"
ROLLING_START_YEAR = 2020
ROLLING_END_YEAR = 2025

OUTPUT_DIR = ROOT / "outputs" / "phase7"
ANNUAL_OUTPUT_PATH = OUTPUT_DIR / "phase7_fcf_annual_tables.csv"
TWO_FACTOR_OUTPUT_PATH = OUTPUT_DIR / "phase7_fcf_two_factor_yoy.csv"
THREE_FACTOR_OUTPUT_PATH = OUTPUT_DIR / "phase7_fcf_three_factor_decomposition.csv"
COMBINED_OUTPUT_PATH = OUTPUT_DIR / "phase7_combined_six_factor_panel.csv"
VALIDATION_OUTPUT_PATH = OUTPUT_DIR / "phase7_fcf_validation_results.csv"
SHEET_STYLE_OUTPUT_PATH = OUTPUT_DIR / "phase7_fcf_factors_sheet_style.csv"
SUMMARY_OUTPUT_PATH = OUTPUT_DIR / "phase7_fcf_summary.md"


def read_csv_rows(path: Path) -> List[List[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.reader(handle))


def read_csv_dicts(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def find_row(rows: Iterable[List[str]], label: str) -> List[str]:
    for row in rows:
        if label in row:
            return row
    raise ValueError(f"Could not find row labeled {label!r}")


def annual_year_columns(model_rows: List[List[str]]) -> Dict[str, int]:
    """Map annual year labels to the annual block in the model export."""

    header_row = model_rows[6]
    mapping: Dict[str, int] = {}

    for index, value in enumerate(header_row):
        if value.endswith("00:00:00"):
            mapping[value[:4]] = index

    return mapping


def years_for_window(start_year: int, end_year: int) -> List[str]:
    return [str(year) for year in range(start_year, end_year + 1)]


def load_model_series(required_years: List[str]) -> Dict[str, Dict[str, float]]:
    model_rows = read_csv_rows(MODEL_PATH)
    year_to_col = annual_year_columns(model_rows)

    series: Dict[str, Dict[str, float]] = {}
    for series_name, row_label in KEY_ROWS.items():
        row = find_row(model_rows, row_label)
        series[series_name] = {
            year: float(row[year_to_col[year]]) for year in required_years
        }

    return series


def build_annual_rows(
    window_label: str,
    years: List[str],
    series: Dict[str, Dict[str, float]],
) -> List[Dict[str, float]]:
    annual_rows: List[Dict[str, float]] = []

    for year in years:
        revenue = series["revenue"][year]
        net_income = series["net_income"][year]
        shares = series["shares"][year]
        free_cash_flow = series["free_cash_flow"][year]

        net_margin = net_income / revenue
        fcf_margin = free_cash_flow / revenue
        rev_per_share = revenue / shares
        eps = net_income / shares
        fcf_per_share = free_cash_flow / shares

        annual_rows.append(
            {
                "window_label": window_label,
                "year": int(year),
                "revenue": revenue,
                "net_income": net_income,
                "free_cash_flow": free_cash_flow,
                "average_diluted_shares": shares,
                "net_margin": net_margin,
                "fcf_margin": fcf_margin,
                "rev_per_share": rev_per_share,
                "eps": eps,
                "fcf_per_share": fcf_per_share,
            }
        )

    return annual_rows


def largest_driver_name(contributions: Dict[str, float]) -> str:
    return max(contributions, key=lambda key: abs(contributions[key]))


def direction(value: float) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "flat"


def absolute_share_weights(contributions: Dict[str, float]) -> Dict[str, float]:
    total = sum(abs(value) for value in contributions.values())
    if total == 0:
        return {key: 0.0 for key in contributions}
    return {key: abs(value) / total for key, value in contributions.items()}


def build_two_factor_rows(
    annual_rows: List[Dict[str, float]],
) -> List[Dict[str, object]]:
    rows_by_window: Dict[str, List[Dict[str, float]]] = {
        window: [] for window, _, _ in WINDOWS
    }
    for row in annual_rows:
        rows_by_window[row["window_label"]].append(row)

    output_rows: List[Dict[str, object]] = []

    for window_label, rows in rows_by_window.items():
        rows.sort(key=lambda row: row["year"])

        for index in range(1, len(rows)):
            previous = rows[index - 1]
            current = rows[index]

            # Exact two-factor bridge: FCF/S = Rev/S x FCF Margin.
            rev_per_share_log = math.log(
                current["rev_per_share"] / previous["rev_per_share"]
            )
            fcf_margin_log = math.log(current["fcf_margin"] / previous["fcf_margin"])
            fcf_per_share_log = math.log(
                current["fcf_per_share"] / previous["fcf_per_share"]
            )

            tie_out_gap = fcf_per_share_log - (rev_per_share_log + fcf_margin_log)

            output_rows.append(
                {
                    "window_label": window_label,
                    "from_year": int(previous["year"]),
                    "to_year": int(current["year"]),
                    "period": f"{int(previous['year'])}-{int(current['year'])}",
                    "delta_rev_per_share_growth": (
                        current["rev_per_share"] / previous["rev_per_share"] - 1
                    ),
                    "delta_fcf_margin_growth": (
                        current["fcf_margin"] / previous["fcf_margin"] - 1
                    ),
                    "delta_fcf_per_share_growth": (
                        current["fcf_per_share"] / previous["fcf_per_share"] - 1
                    ),
                    "rev_per_share_log_contribution": rev_per_share_log,
                    "fcf_margin_log_contribution": fcf_margin_log,
                    "fcf_per_share_log_change": fcf_per_share_log,
                    "two_factor_tie_out_gap": tie_out_gap,
                    "dominant_two_factor": (
                        "rev_per_share"
                        if abs(rev_per_share_log) >= abs(fcf_margin_log)
                        else "fcf_margin"
                    ),
                }
            )

    return output_rows


def build_three_factor_rows(
    annual_rows: List[Dict[str, float]],
) -> List[Dict[str, object]]:
    rows_by_window: Dict[str, List[Dict[str, float]]] = {
        window: [] for window, _, _ in WINDOWS
    }
    for row in annual_rows:
        rows_by_window[row["window_label"]].append(row)

    output_rows: List[Dict[str, object]] = []

    for window_label, rows in rows_by_window.items():
        rows.sort(key=lambda row: row["year"])

        for index in range(1, len(rows)):
            previous = rows[index - 1]
            current = rows[index]

            revenue_growth = current["revenue"] / previous["revenue"] - 1
            fcf_margin_growth = current["fcf_margin"] / previous["fcf_margin"] - 1
            shares_growth = (
                current["average_diluted_shares"]
                / previous["average_diluted_shares"]
                - 1
            )
            fcf_per_share_growth = (
                current["fcf_per_share"] / previous["fcf_per_share"] - 1
            )

            # Exact three-factor bridge: FCF/S = Revenue x FCF Margin / Shares.
            revenue_log = math.log(current["revenue"] / previous["revenue"])
            fcf_margin_log = math.log(current["fcf_margin"] / previous["fcf_margin"])
            share_count_log = -math.log(
                current["average_diluted_shares"]
                / previous["average_diluted_shares"]
            )
            fcf_per_share_log = math.log(
                current["fcf_per_share"] / previous["fcf_per_share"]
            )

            contributions = {
                "revenue": revenue_log,
                "fcf_margin": fcf_margin_log,
                "share_count": share_count_log,
            }
            tie_out_gap = fcf_per_share_log - sum(contributions.values())

            ranked = sorted(
                contributions.items(), key=lambda item: abs(item[1]), reverse=True
            )
            weights = absolute_share_weights(contributions)
            largest_driver = ranked[0][0]
            largest_value = ranked[0][1]

            has_offsetting_factors = any(value > 0 for value in contributions.values()) and any(
                value < 0 for value in contributions.values()
            )

            output_rows.append(
                {
                    "window_label": window_label,
                    "from_year": int(previous["year"]),
                    "to_year": int(current["year"]),
                    "period": f"{int(previous['year'])}-{int(current['year'])}",
                    "revenue_growth": revenue_growth,
                    "fcf_margin_growth": fcf_margin_growth,
                    "share_count_growth": shares_growth,
                    "fcf_per_share_growth": fcf_per_share_growth,
                    "share_count_effect_simple": -shares_growth,
                    "revenue_log_contribution": revenue_log,
                    "fcf_margin_log_contribution": fcf_margin_log,
                    "share_count_log_contribution": share_count_log,
                    "rev_per_share_log_contribution": revenue_log + share_count_log,
                    "fcf_per_share_log_change": fcf_per_share_log,
                    "tie_out_gap": tie_out_gap,
                    "rank_1_factor": ranked[0][0],
                    "rank_1_log_contribution": ranked[0][1],
                    "rank_2_factor": ranked[1][0],
                    "rank_2_log_contribution": ranked[1][1],
                    "rank_3_factor": ranked[2][0],
                    "rank_3_log_contribution": ranked[2][1],
                    "revenue_weight_abs_share": weights["revenue"],
                    "fcf_margin_weight_abs_share": weights["fcf_margin"],
                    "share_count_weight_abs_share": weights["share_count"],
                    "largest_driver": largest_driver,
                    "largest_driver_direction": direction(largest_value),
                    "largest_driver_abs_log_contribution": abs(largest_value),
                    "has_offsetting_factors": "yes" if has_offsetting_factors else "no",
                    "fcf_per_share_direction": direction(fcf_per_share_growth),
                }
            )

    return output_rows


def load_phase3_decomposition() -> List[Dict[str, str]]:
    return read_csv_dicts(PHASE3_DECOMP_PATH)


def build_combined_panel(
    eps_rows: List[Dict[str, str]],
    fcf_rows: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    eps_by_key = {
        (row["window_label"], row["period"]): row for row in eps_rows
    }

    combined_rows: List[Dict[str, object]] = []

    for fcf_row in fcf_rows:
        key = (fcf_row["window_label"], fcf_row["period"])
        eps_row = eps_by_key.get(key)
        if eps_row is None:
            continue

        eps_revenue = float(eps_row["revenue_log_contribution"])
        eps_net_margin = float(eps_row["net_margin_log_contribution"])
        eps_share_count = float(eps_row["share_count_log_contribution"])
        eps_log_change = float(eps_row["eps_log_change"])

        fcf_revenue = float(fcf_row["revenue_log_contribution"])
        fcf_margin = float(fcf_row["fcf_margin_log_contribution"])
        fcf_share_count = float(fcf_row["share_count_log_contribution"])
        fcf_log_change = float(fcf_row["fcf_per_share_log_change"])

        eps_contribs = {
            "eps_revenue": eps_revenue,
            "eps_net_margin": eps_net_margin,
            "eps_share_count": eps_share_count,
        }
        fcf_contribs = {
            "fcf_revenue": fcf_revenue,
            "fcf_margin": fcf_margin,
            "fcf_share_count": fcf_share_count,
        }
        eps_weights = absolute_share_weights(eps_contribs)
        fcf_weights = absolute_share_weights(fcf_contribs)

        combined_rows.append(
            {
                "window_label": fcf_row["window_label"],
                "period": fcf_row["period"],
                "eps_revenue_log_contribution": eps_revenue,
                "eps_net_margin_log_contribution": eps_net_margin,
                "eps_share_count_log_contribution": eps_share_count,
                "eps_log_change": eps_log_change,
                "fcf_revenue_log_contribution": fcf_revenue,
                "fcf_margin_log_contribution": fcf_margin,
                "fcf_share_count_log_contribution": fcf_share_count,
                "fcf_per_share_log_change": fcf_log_change,
                "eps_revenue_weight": eps_weights["eps_revenue"],
                "eps_net_margin_weight": eps_weights["eps_net_margin"],
                "eps_share_count_weight": eps_weights["eps_share_count"],
                "fcf_revenue_weight": fcf_weights["fcf_revenue"],
                "fcf_margin_weight": fcf_weights["fcf_margin"],
                "fcf_share_count_weight": fcf_weights["fcf_share_count"],
                "net_margin_minus_fcf_margin_contribution": eps_net_margin - fcf_margin,
                "share_count_sensitivity_gap": fcf_share_count - eps_share_count,
            }
        )

    return combined_rows


def pearson_correlation(
    x_values: Sequence[float], y_values: Sequence[float]
) -> float:
    if len(x_values) != len(y_values):
        raise ValueError("Correlation inputs must have the same length")
    if len(x_values) < 2:
        return float("nan")

    mean_x = statistics.fmean(x_values)
    mean_y = statistics.fmean(y_values)

    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in x_values))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in y_values))

    if denom_x == 0 or denom_y == 0:
        return float("nan")

    return numerator / (denom_x * denom_y)


def full_window_rows(
    rows: Iterable[Dict[str, object]], window_label: str = "2001_2025"
) -> List[Dict[str, object]]:
    return [row for row in rows if row["window_label"] == window_label]


def rolling_rows(rows: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    return [
        row
        for row in rows
        if row["window_label"] == ROLLING_WINDOW_LABEL
        and int(row["from_year"]) >= ROLLING_START_YEAR
        and int(row["to_year"]) <= ROLLING_END_YEAR
    ]


def factor_stats(rows: List[Dict[str, object]], factor_key: str) -> Dict[str, float]:
    values = [float(row[factor_key]) for row in rows]
    return {
        "positive_count": sum(1 for value in values if value > 0),
        "mean": statistics.fmean(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def build_validation_rows(
    annual_rows: List[Dict[str, float]],
    two_factor_rows: List[Dict[str, object]],
    three_factor_rows: List[Dict[str, object]],
    combined_rows: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    validation_rows: List[Dict[str, object]] = []

    for window_label, start_year, end_year in WINDOWS:
        annual_count = sum(
            1 for row in annual_rows if row["window_label"] == window_label
        )
        two_factor_count = sum(
            1 for row in two_factor_rows if row["window_label"] == window_label
        )
        three_factor_count = sum(
            1 for row in three_factor_rows if row["window_label"] == window_label
        )

        expected_annual = end_year - start_year + 1
        expected_periods = expected_annual - 1

        validation_rows.append(
            {
                "test_name": f"{window_label}_annual_row_count",
                "status": "PASS" if annual_count == expected_annual else "FAIL",
                "details": f"expected {expected_annual}, got {annual_count}",
            }
        )
        validation_rows.append(
            {
                "test_name": f"{window_label}_two_factor_row_count",
                "status": "PASS" if two_factor_count == expected_periods else "FAIL",
                "details": f"expected {expected_periods}, got {two_factor_count}",
            }
        )
        validation_rows.append(
            {
                "test_name": f"{window_label}_three_factor_row_count",
                "status": "PASS"
                if three_factor_count == expected_periods
                else "FAIL",
                "details": f"expected {expected_periods}, got {three_factor_count}",
            }
        )

    # Annual identity should hold exactly from the base accounting rows.
    max_identity_gap = max(
        abs(
            row["fcf_per_share"]
            - (row["revenue"] * row["fcf_margin"] / row["average_diluted_shares"])
        )
        for row in annual_rows
    )
    validation_rows.append(
        {
            "test_name": "annual_fcf_identity_tie_out",
            "status": "PASS" if max_identity_gap < 1e-9 else "FAIL",
            "details": f"max gap {max_identity_gap:.12f}",
        }
    )

    max_two_factor_gap = max(
        abs(float(row["two_factor_tie_out_gap"])) for row in two_factor_rows
    )
    validation_rows.append(
        {
            "test_name": "exact_two_factor_tie_out",
            "status": "PASS" if max_two_factor_gap < 1e-12 else "FAIL",
            "details": f"max gap {max_two_factor_gap:.12f}",
        }
    )

    max_three_factor_gap = max(
        abs(float(row["tie_out_gap"])) for row in three_factor_rows
    )
    validation_rows.append(
        {
            "test_name": "exact_three_factor_tie_out",
            "status": "PASS" if max_three_factor_gap < 1e-12 else "FAIL",
            "details": f"max gap {max_three_factor_gap:.12f}",
        }
    )

    # Log decomposition requires positive values.
    all_positive = all(
        row["revenue"] > 0
        and row["fcf_margin"] > 0
        and row["average_diluted_shares"] > 0
        and row["fcf_per_share"] > 0
        for row in annual_rows
    )
    validation_rows.append(
        {
            "test_name": "all_phase7_inputs_positive",
            "status": "PASS" if all_positive else "FAIL",
            "details": "checked revenue, fcf_margin, shares, and fcf_per_share",
        }
    )

    # When share count falls, the directional share effect should read positive.
    directional_ok = all(
        (
            float(row["share_count_growth"]) < 0
            and float(row["share_count_log_contribution"]) > 0
        )
        or (
            float(row["share_count_growth"]) > 0
            and float(row["share_count_log_contribution"]) < 0
        )
        or (
            float(row["share_count_growth"]) == 0
            and float(row["share_count_log_contribution"]) == 0
        )
        for row in three_factor_rows
    )
    validation_rows.append(
        {
            "test_name": "share_count_directionality_check",
            "status": "PASS" if directional_ok else "FAIL",
            "details": "buybacks map to positive share-count contribution",
        }
    )

    # Absolute-share weights must sum to 1 per period (within tolerance).
    max_weight_gap = max(
        abs(
            float(row["revenue_weight_abs_share"])
            + float(row["fcf_margin_weight_abs_share"])
            + float(row["share_count_weight_abs_share"])
            - 1.0
        )
        for row in three_factor_rows
    )
    validation_rows.append(
        {
            "test_name": "fcf_abs_share_weights_sum_to_one",
            "status": "PASS" if max_weight_gap < 1e-9 else "FAIL",
            "details": f"max deviation {max_weight_gap:.12f}",
        }
    )

    # Combined panel should cover every 2001-2025 EPS period.
    eps_periods = sum(
        1 for row in three_factor_rows if row["window_label"] == "2001_2025"
    )
    combined_periods = sum(
        1 for row in combined_rows if row["window_label"] == "2001_2025"
    )
    validation_rows.append(
        {
            "test_name": "combined_panel_join_complete",
            "status": "PASS" if combined_periods == eps_periods else "FAIL",
            "details": f"expected {eps_periods}, got {combined_periods}",
        }
    )

    return validation_rows


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows were generated for {path.name}")

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_sheet_style(annual_rows: List[Dict[str, float]]) -> None:
    """Mirror the Sheet1 layout but for the FCF factor block.

    The formula-sheet convention is the simple additive bridge the user
    described: dFCF = dRev/Share + dFCF Margin (simple year-over-year growth
    rates). The exact log decomposition lives in the main CSVs.
    """

    sheet_rows = [
        row
        for row in annual_rows
        if row["window_label"] == "2015_2025"
        and SHEET_START_YEAR <= row["year"] <= SHEET_END_YEAR
    ]
    sheet_rows.sort(key=lambda row: row["year"])

    delta_rev_per_share: List[float] = []
    delta_fcf_margin: List[float] = []
    delta_fcf: List[float] = []
    # EPS-side deltas reproduced for the six-factor comparison block.
    delta_net_margin: List[float] = []
    delta_eps: List[float] = []

    for index in range(1, len(sheet_rows)):
        previous = sheet_rows[index - 1]
        current = sheet_rows[index]

        d_rev_per_share = current["rev_per_share"] / previous["rev_per_share"] - 1
        d_fcf_margin = current["fcf_margin"] / previous["fcf_margin"] - 1
        d_net_margin = current["net_margin"] / previous["net_margin"] - 1

        delta_rev_per_share.append(d_rev_per_share)
        delta_fcf_margin.append(d_fcf_margin)
        delta_fcf.append(d_rev_per_share + d_fcf_margin)
        delta_net_margin.append(d_net_margin)
        delta_eps.append(d_rev_per_share + d_net_margin)

    year_labels = [str(row["year"]) for row in sheet_rows]

    def fmt(values: List[float]) -> List[str]:
        return [f"{value:.10f}" for value in values]

    lines: List[List[str]] = []
    lines.append(["", "", "Year", "Year", "Year", "Year", "Year"])
    lines.append(["", "", "1", "2", "3", "4", "5"])
    lines.append(["", "delta Rev/Share"] + fmt(delta_rev_per_share))
    lines.append(["", "delta FCFMargin"] + fmt(delta_fcf_margin))
    lines.append(["", "delta FCF (additive)"] + fmt(delta_fcf))
    lines.append([])
    lines.append(["", "Six-factor comparison (EPS block)"])
    lines.append(["", "delta Rev/Share"] + fmt(delta_rev_per_share))
    lines.append(["", "delta NetMargin"] + fmt(delta_net_margin))
    lines.append(["", "delta EPS (additive)"] + fmt(delta_eps))
    lines.append([])
    lines.append([])
    lines.append([""] + year_labels)
    lines.append(["Rev ($m)"] + [f"{row['revenue']:.3f}" for row in sheet_rows])
    lines.append(["FCF ($m)"] + [f"{row['free_cash_flow']:.3f}" for row in sheet_rows])
    lines.append(
        ["Net Income ($m)"] + [f"{row['net_income']:.3f}" for row in sheet_rows]
    )
    lines.append(
        ["#Shares(m)"]
        + [f"{row['average_diluted_shares']:.3f}" for row in sheet_rows]
    )
    lines.append([])
    lines.append(["Rev/S"] + [f"{row['rev_per_share']:.10f}" for row in sheet_rows])
    lines.append(
        ["FCFMargin"] + [f"{row['fcf_margin']:.10f}" for row in sheet_rows]
    )
    lines.append(["FCF/S"] + [f"{row['fcf_per_share']:.10f}" for row in sheet_rows])
    lines.append(
        ["NetMargin"] + [f"{row['net_margin']:.10f}" for row in sheet_rows]
    )

    with SHEET_STYLE_OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerows(lines)


def md_table(headers: List[str], rows: List[List[str]]) -> List[str]:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def fmt4(value: float) -> str:
    if isinstance(value, str):
        value = float(value)
    if math.isnan(value):
        return "N/A"
    return f"{value:.4f}"


def fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def write_summary(
    two_factor_rows: List[Dict[str, object]],
    three_factor_rows: List[Dict[str, object]],
    combined_rows: List[Dict[str, object]],
    validation_rows: List[Dict[str, object]],
) -> None:
    failing = [row for row in validation_rows if row["status"] != "PASS"]

    full_three = full_window_rows(three_factor_rows)
    rolling = rolling_rows(three_factor_rows)

    largest_swing = max(
        full_three,
        key=lambda row: float(row["largest_driver_abs_log_contribution"]),
    )

    rolling_factor_map = {
        "revenue": "revenue_log_contribution",
        "fcf_margin": "fcf_margin_log_contribution",
        "share_count": "share_count_log_contribution",
    }
    rolling_stats = {
        factor: factor_stats(rolling, key)
        for factor, key in rolling_factor_map.items()
    }
    most_consistent = max(
        rolling_stats.items(),
        key=lambda item: (item[1]["positive_count"], item[1]["mean"]),
    )[0]
    most_volatile = max(rolling_stats.items(), key=lambda item: item[1]["stdev"])[0]
    offsetting_rolling = [
        row["period"] for row in rolling if row["has_offsetting_factors"] == "yes"
    ]

    # Correlation & relationships (FCF).
    revenue_growth_values = [float(row["revenue_growth"]) for row in full_three]
    significant_threshold = statistics.quantiles(
        revenue_growth_values, n=4, method="inclusive"
    )[2]
    significant_rows = [
        row
        for row in full_three
        if float(row["revenue_growth"]) >= significant_threshold
    ]
    sig_expand = sum(
        1 for row in significant_rows if float(row["fcf_margin_growth"]) > 0
    )
    sig_contract = sum(
        1 for row in significant_rows if float(row["fcf_margin_growth"]) < 0
    )
    sig_flat = len(significant_rows) - sig_expand - sig_contract

    revenue_fcf_margin_corr = pearson_correlation(
        [float(row["revenue_growth"]) for row in full_three],
        [float(row["fcf_margin_growth"]) for row in full_three],
    )

    margin_down_fcf_up = [
        row
        for row in full_three
        if float(row["fcf_margin_growth"]) < 0
        and float(row["fcf_per_share_growth"]) > 0
    ]
    revenue_enough = [
        row
        for row in margin_down_fcf_up
        if float(row["revenue_log_contribution"])
        > abs(
            float(row["fcf_margin_log_contribution"])
            + float(row["share_count_log_contribution"])
        )
    ]

    buyback_rows = [row for row in full_three if float(row["share_count_growth"]) < 0]
    buyback_rev_corr = pearson_correlation(
        [float(row["share_count_log_contribution"]) for row in buyback_rows],
        [float(row["revenue_log_contribution"]) for row in buyback_rows],
    )
    buyback_margin_corr = pearson_correlation(
        [float(row["share_count_log_contribution"]) for row in buyback_rows],
        [float(row["fcf_margin_log_contribution"]) for row in buyback_rows],
    )

    # Six-factor cross comparison.
    full_combined = full_window_rows(combined_rows)
    net_vs_fcf_margin_corr = pearson_correlation(
        [float(row["eps_net_margin_log_contribution"]) for row in full_combined],
        [float(row["fcf_margin_log_contribution"]) for row in full_combined],
    )
    eps_share_abs = statistics.fmean(
        [abs(float(row["eps_share_count_log_contribution"])) for row in full_combined]
    )
    fcf_share_abs = statistics.fmean(
        [abs(float(row["fcf_share_count_log_contribution"])) for row in full_combined]
    )

    lines: List[str] = [
        "# Phase 7 FCF Factor Decomposition Summary",
        "",
        "## Testing",
        "",
        (
            "All Phase 7 validation checks passed."
            if not failing
            else "Phase 7 completed with validation FAILURES: "
            + ", ".join(row["test_name"] for row in failing)
        ),
        "",
        "Validation file: `outputs/phase7/phase7_fcf_validation_results.csv`",
        "",
        "## Method",
        "",
        "- Two-factor FCF bridge: `FCF/S = Rev/S x FCF Margin`.",
        "- Three-factor FCF bridge: `FCF/S = Revenue x FCF Margin / Shares`.",
        "- Contributions are exact log contributions, so they tie out to total FCF/S movement.",
        "- Weights are absolute-contribution shares: `|c_i| / sum_j |c_j|` (positive, sum to 100%).",
        "- Positive contribution helps FCF/S; negative hurts it. Share count is signed so buybacks read positive.",
        "- Diluted shares are on a consistent split-adjusted basis across all years (pre-split 2001-2013 restated x20).",
        "",
        "## A. The 3 FCF Factors",
        "",
        "### Replication & Expansion (two-factor: Rev/S + FCF Margin)",
        "",
    ]

    for window_label, _, _ in WINDOWS:
        window_rows = [
            row for row in two_factor_rows if row["window_label"] == window_label
        ]
        window_rows.sort(key=lambda row: int(row["from_year"]))
        table_rows = [
            [
                str(row["period"]),
                fmt4(row["rev_per_share_log_contribution"]),
                fmt4(row["fcf_margin_log_contribution"]),
                fmt4(row["fcf_per_share_log_change"]),
                str(row["dominant_two_factor"]),
            ]
            for row in window_rows
        ]
        label_map = {
            "2015_2025": "Years 1-10: 2015-2025",
            "2010_2025": "Years 1-15: 2010-2025",
            "2001_2025": "Years 1-20: 2001-2025",
        }
        lines.append(f"#### {label_map[window_label]}")
        lines.append("")
        lines.extend(
            md_table(
                [
                    "Period",
                    "Rev/S Contribution",
                    "FCF Margin Contribution",
                    "FCF/S Change",
                    "Dominant 2-Factor Driver",
                ],
                table_rows,
            )
        )
        lines.append("")

    lines.extend(
        [
            "### Year-Over-Year Decomposition (three-factor, full 2001-2025)",
            "",
        ]
    )
    yoy_rows = [
        [
            str(row["period"]),
            fmt4(row["revenue_log_contribution"]),
            fmt4(row["fcf_margin_log_contribution"]),
            fmt4(row["share_count_log_contribution"]),
            str(row["rank_1_factor"]),
            str(row["rank_2_factor"]),
            str(row["rank_3_factor"]),
            str(row["largest_driver"]),
            str(row["largest_driver_direction"]),
        ]
        for row in sorted(full_three, key=lambda row: int(row["from_year"]))
    ]
    lines.extend(
        md_table(
            [
                "Period",
                "Revenue",
                "FCF Margin",
                "Share Count",
                "Rank 1",
                "Rank 2",
                "Rank 3",
                "Largest Driver",
                "Direction",
            ],
            yoy_rows,
        )
    )
    lines.extend(
        [
            "",
            f"- Largest single-factor FCF/S swing (2001-2025): `{largest_swing['largest_driver']}` in `{largest_swing['period']}`, `{largest_swing['largest_driver_direction']}`.",
            "",
            "### Five-Year Rolling Analysis (2020-2025)",
            "",
            f"- Most consistent positive FCF contributor: `{most_consistent}`.",
            f"- Most volatile factor: `{most_volatile}`.",
            f"- Offsetting factor moves occurred in: `{', '.join(offsetting_rolling) if offsetting_rolling else 'none'}`.",
            "",
        ]
    )
    rolling_table = [
        [
            factor,
            str(int(rolling_stats[factor]["positive_count"])),
            fmt4(rolling_stats[factor]["mean"]),
            fmt4(rolling_stats[factor]["stdev"]),
        ]
        for factor in ["revenue", "fcf_margin", "share_count"]
    ]
    lines.extend(
        md_table(
            ["Factor", "Positive Periods (of 5)", "Mean", "Std Dev"], rolling_table
        )
    )
    lines.extend(
        [
            "",
            "### Correlation & Relationships (FCF)",
            "",
            f"- Revenue growth vs FCF-margin change correlation (2001-2025): `{fmt4(revenue_fcf_margin_corr)}`.",
            f"- In top-quartile revenue-growth years (threshold `{fmt4(significant_threshold)}`), FCF margin expanded in `{sig_expand}`, contracted in `{sig_contract}`, flat in `{sig_flat}`.",
            f"- FCF margin contracted yet FCF/S still rose in `{len(margin_down_fcf_up)}` periods; revenue alone outweighed the combined drag in `{len(revenue_enough)}` of them.",
            f"- For buyback years, share-count contribution correlates `{fmt4(buyback_rev_corr)}` with revenue and `{fmt4(buyback_margin_corr)}` with FCF margin.",
            (
                "  The buyback lift aligns more strongly with revenue than FCF margin."
                if abs(buyback_rev_corr) > abs(buyback_margin_corr)
                else "  The buyback lift aligns more strongly with FCF margin than revenue."
            ),
            "",
            "## B. All 6 Factors (EPS + FCF cross comparison)",
            "",
            f"- Net-margin vs FCF-margin log-contribution correlation (2001-2025): `{fmt4(net_vs_fcf_margin_corr)}`.",
            f"- Mean absolute share-count contribution: EPS `{fmt4(eps_share_abs)}` vs FCF/S `{fmt4(fcf_share_abs)}`.",
            (
                "  Share count enters both identities identically (same diluted share base), so neither EPS nor FCF/S is structurally more share-count sensitive: the buyback lift is the same for both. The amplification differs only through which margin (net vs FCF) the share effect is paired with."
                if abs(fcf_share_abs - eps_share_abs) < 1e-9
                else (
                    "  FCF/S is more share-count sensitive than EPS on average."
                    if fcf_share_abs > eps_share_abs
                    else "  EPS is more share-count sensitive than FCF/S on average."
                )
            ),
            "- Full per-period six-factor weights are in `outputs/phase7/phase7_combined_six_factor_panel.csv`.",
            "",
            "## Output Files",
            "",
            "- `outputs/phase7/phase7_fcf_annual_tables.csv`",
            "- `outputs/phase7/phase7_fcf_two_factor_yoy.csv`",
            "- `outputs/phase7/phase7_fcf_three_factor_decomposition.csv`",
            "- `outputs/phase7/phase7_combined_six_factor_panel.csv`",
            "- `outputs/phase7/phase7_fcf_validation_results.csv`",
            "- `outputs/phase7/phase7_fcf_factors_sheet_style.csv`",
            "- `outputs/phase7/phase7_fcf_summary.md`",
        ]
    )

    SUMMARY_OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_years = sorted(
        {
            str(year)
            for _, start_year, end_year in WINDOWS
            for year in range(start_year, end_year + 1)
        }
    )
    model_series = load_model_series(all_years)

    annual_rows: List[Dict[str, float]] = []
    for window_label, start_year, end_year in WINDOWS:
        years = years_for_window(start_year, end_year)
        annual_rows.extend(build_annual_rows(window_label, years, model_series))

    two_factor_rows = build_two_factor_rows(annual_rows)
    three_factor_rows = build_three_factor_rows(annual_rows)

    eps_rows = load_phase3_decomposition()
    combined_rows = build_combined_panel(eps_rows, three_factor_rows)

    validation_rows = build_validation_rows(
        annual_rows, two_factor_rows, three_factor_rows, combined_rows
    )

    write_csv(ANNUAL_OUTPUT_PATH, annual_rows)
    write_csv(TWO_FACTOR_OUTPUT_PATH, two_factor_rows)
    write_csv(THREE_FACTOR_OUTPUT_PATH, three_factor_rows)
    write_csv(COMBINED_OUTPUT_PATH, combined_rows)
    write_csv(VALIDATION_OUTPUT_PATH, validation_rows)
    write_sheet_style(annual_rows)
    write_summary(two_factor_rows, three_factor_rows, combined_rows, validation_rows)

    print(f"Wrote {ANNUAL_OUTPUT_PATH.name}")
    print(f"Wrote {TWO_FACTOR_OUTPUT_PATH.name}")
    print(f"Wrote {THREE_FACTOR_OUTPUT_PATH.name}")
    print(f"Wrote {COMBINED_OUTPUT_PATH.name}")
    print(f"Wrote {VALIDATION_OUTPUT_PATH.name}")
    print(f"Wrote {SHEET_STYLE_OUTPUT_PATH.name}")
    print(f"Wrote {SUMMARY_OUTPUT_PATH.name}")

    failing = [row for row in validation_rows if row["status"] != "PASS"]
    if failing:
        print("VALIDATION FAILURES:")
        for row in failing:
            print(f"  {row['test_name']}: {row['details']}")
    else:
        print("All validation checks PASSED.")


if __name__ == "__main__":
    main()
