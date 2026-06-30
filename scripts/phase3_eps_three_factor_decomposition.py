#!/usr/bin/env python3
"""Build the Phase 3 three-factor EPS decomposition.

Phase 3 shifts from the formulas-sheet approximation to the more complete
identity:

    EPS = Revenue x Net Margin / Shares

For each adjacent year-over-year period in the requested windows, this script:

1. Rebuilds the annual driver table from `Model.csv`
2. Calculates simple growth rates for Revenue, Margin, Shares, and EPS
3. Calculates an exact additive decomposition using log contributions
4. Ranks the three factors by contribution magnitude
5. Writes explicit validation outputs so the phase is test-backed

The log-form contribution method is used because it ties out exactly:

    log(EPS_t / EPS_t-1)
    = log(Revenue_t / Revenue_t-1)
    + log(Margin_t / Margin_t-1)
    - log(Shares_t / Shares_t-1)

Outputs:

- `phase3_eps_annual_tables.csv`
- `phase3_eps_three_factor_decomposition.csv`
- `phase3_eps_validation_results.csv`
- `phase3_eps_summary.md`
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "data" / "GOOG MS ML 10-Year Actuals" / "Model.csv"

KEY_ROWS = {
    "revenue": "Total Gross revenue (GAAP)",
    "net_income": "Net income, reported",
    "shares": "Average diluted shares",
}

WINDOWS: List[Tuple[str, int, int]] = [
    ("2015_2025", 2015, 2025),
    ("2010_2025", 2010, 2025),
    ("2001_2025", 2001, 2025),
]

ANNUAL_OUTPUT_PATH = ROOT / "outputs" / "phase3" / "phase3_eps_annual_tables.csv"
DECOMPOSITION_OUTPUT_PATH = ROOT / "outputs" / "phase3" / "phase3_eps_three_factor_decomposition.csv"
VALIDATION_OUTPUT_PATH = ROOT / "outputs" / "phase3" / "phase3_eps_validation_results.csv"
SUMMARY_OUTPUT_PATH = ROOT / "outputs" / "phase3" / "phase3_eps_summary.md"


def read_csv_rows(path: Path) -> List[List[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.reader(handle))


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
            year: float(row[year_to_col[year]])
            for year in required_years
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
        net_margin = net_income / revenue
        rev_per_share = revenue / shares
        eps = net_income / shares

        annual_rows.append(
            {
                "window_label": window_label,
                "year": int(year),
                "revenue": revenue,
                "net_income": net_income,
                "average_diluted_shares": shares,
                "net_margin": net_margin,
                "rev_per_share": rev_per_share,
                "eps": eps,
            }
        )

    return annual_rows


def largest_driver_name(contributions: Dict[str, float]) -> str:
    return max(contributions, key=lambda key: abs(contributions[key]))


def largest_driver_direction(value: float) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "flat"


def build_decomposition_rows(
    window_label: str,
    annual_rows: List[Dict[str, float]],
) -> List[Dict[str, object]]:
    decomposition_rows: List[Dict[str, object]] = []

    for index in range(1, len(annual_rows)):
        previous = annual_rows[index - 1]
        current = annual_rows[index]

        revenue_growth = current["revenue"] / previous["revenue"] - 1
        margin_growth = current["net_margin"] / previous["net_margin"] - 1
        shares_growth = current["average_diluted_shares"] / previous[
            "average_diluted_shares"
        ] - 1
        eps_growth = current["eps"] / previous["eps"] - 1

        # Log contributions provide an exact additive bridge for a multiplicative
        # identity. That makes testing cleaner and keeps the factor ranking
        # stable even when multiple drivers move sharply at the same time.
        revenue_log_contribution = math.log(current["revenue"] / previous["revenue"])
        margin_log_contribution = math.log(
            current["net_margin"] / previous["net_margin"]
        )
        share_count_log_contribution = -math.log(
            current["average_diluted_shares"] / previous["average_diluted_shares"]
        )
        eps_log_change = math.log(current["eps"] / previous["eps"])

        tie_out_gap = eps_log_change - (
            revenue_log_contribution
            + margin_log_contribution
            + share_count_log_contribution
        )

        contributions = {
            "revenue": revenue_log_contribution,
            "net_margin": margin_log_contribution,
            "share_count": share_count_log_contribution,
        }
        largest_driver = largest_driver_name(contributions)
        largest_driver_value = contributions[largest_driver]

        decomposition_rows.append(
            {
                "window_label": window_label,
                "from_year": int(previous["year"]),
                "to_year": int(current["year"]),
                "period": f"{int(previous['year'])}-{int(current['year'])}",
                "revenue_growth": revenue_growth,
                "net_margin_growth": margin_growth,
                "share_count_growth": shares_growth,
                "eps_growth": eps_growth,
                "share_count_effect_simple": -shares_growth,
                "revenue_log_contribution": revenue_log_contribution,
                "net_margin_log_contribution": margin_log_contribution,
                "share_count_log_contribution": share_count_log_contribution,
                "rev_per_share_log_contribution": (
                    revenue_log_contribution + share_count_log_contribution
                ),
                "eps_log_change": eps_log_change,
                "tie_out_gap": tie_out_gap,
                "largest_driver": largest_driver,
                "largest_driver_direction": largest_driver_direction(
                    largest_driver_value
                ),
                "largest_driver_abs_log_contribution": abs(largest_driver_value),
            }
        )

    return decomposition_rows


def build_validation_rows(
    annual_rows: List[Dict[str, float]],
    decomposition_rows: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    validation_rows: List[Dict[str, object]] = []

    for window_label, start_year, end_year in WINDOWS:
        annual_count = sum(1 for row in annual_rows if row["window_label"] == window_label)
        decomposition_count = sum(
            1 for row in decomposition_rows if row["window_label"] == window_label
        )

        expected_annual_count = end_year - start_year + 1
        expected_decomposition_count = expected_annual_count - 1

        validation_rows.append(
            {
                "test_name": f"{window_label}_annual_row_count",
                "status": "PASS" if annual_count == expected_annual_count else "FAIL",
                "details": f"expected {expected_annual_count}, got {annual_count}",
            }
        )
        validation_rows.append(
            {
                "test_name": f"{window_label}_decomposition_row_count",
                "status": (
                    "PASS"
                    if decomposition_count == expected_decomposition_count
                    else "FAIL"
                ),
                "details": (
                    f"expected {expected_decomposition_count}, got {decomposition_count}"
                ),
            }
        )

    # The annual identity should hold exactly from the base accounting rows.
    max_identity_gap = max(
        abs(
            row["eps"]
            - (
                row["revenue"]
                * row["net_margin"]
                / row["average_diluted_shares"]
            )
        )
        for row in annual_rows
    )
    validation_rows.append(
        {
            "test_name": "annual_eps_identity_tie_out",
            "status": "PASS" if max_identity_gap < 1e-12 else "FAIL",
            "details": f"max gap {max_identity_gap:.12f}",
        }
    )

    # The whole point of the log method is exact additivity, so enforce that.
    max_tie_out_gap = max(abs(float(row["tie_out_gap"])) for row in decomposition_rows)
    validation_rows.append(
        {
            "test_name": "exact_log_decomposition_tie_out",
            "status": "PASS" if max_tie_out_gap < 1e-12 else "FAIL",
            "details": f"max gap {max_tie_out_gap:.12f}",
        }
    )

    # Log decomposition requires positive values. This test confirms the window
    # data is safe for that method.
    all_positive = all(
        row["revenue"] > 0
        and row["net_margin"] > 0
        and row["average_diluted_shares"] > 0
        and row["eps"] > 0
        for row in annual_rows
    )
    validation_rows.append(
        {
            "test_name": "all_phase3_inputs_positive",
            "status": "PASS" if all_positive else "FAIL",
            "details": "checked revenue, margin, shares, and eps across all windows",
        }
    )

    # When share count falls, the directional share effect should read positive.
    directional_ok = all(
        (
            row["share_count_growth"] < 0
            and row["share_count_log_contribution"] > 0
        )
        or (
            row["share_count_growth"] > 0
            and row["share_count_log_contribution"] < 0
        )
        or (
            row["share_count_growth"] == 0
            and row["share_count_log_contribution"] == 0
        )
        for row in decomposition_rows
    )
    validation_rows.append(
        {
            "test_name": "share_count_directionality_check",
            "status": "PASS" if directional_ok else "FAIL",
            "details": "buybacks map to positive share-count contribution",
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


def write_summary(
    annual_rows: List[Dict[str, float]],
    decomposition_rows: List[Dict[str, object]],
    validation_rows: List[Dict[str, object]],
) -> None:
    failing_tests = [row for row in validation_rows if row["status"] != "PASS"]
    max_tie_out_gap = max(abs(float(row["tie_out_gap"])) for row in decomposition_rows)
    max_abs_driver = max(
        float(row["largest_driver_abs_log_contribution"])
        for row in decomposition_rows
    )

    lines = [
        "# Phase 3 EPS Three-Factor Decomposition Summary",
        "",
        "## What this does",
        "",
        "- Builds the full year-over-year three-factor EPS decomposition.",
        "- Splits EPS change into Revenue, Net Margin, and Share Count effects.",
        "- Uses exact log contributions so the factor bridge ties out cleanly.",
        "- Adds largest-driver labeling to support the next analysis phase.",
        "",
        "## Windows covered",
        "",
    ]

    for window_label, _, _ in WINDOWS:
        annual_count = sum(1 for row in annual_rows if row["window_label"] == window_label)
        decomposition_count = sum(
            1 for row in decomposition_rows if row["window_label"] == window_label
        )
        lines.append(
            f"- `{window_label}`: {annual_count} annual rows, {decomposition_count} year-over-year rows"
        )

    lines.extend(
        [
            "",
            "## Testing",
            "",
            "- Row counts were validated for each requested window.",
            "- The annual accounting identity `EPS = Revenue x Net Margin / Shares` was tested.",
            "- The exact log decomposition was tested to tie out back to EPS change.",
            "- Share-count directionality was tested so buybacks read as positive EPS support.",
            "",
            "## Result",
            "",
            (
                "Phase 3 decomposition completed successfully."
                if not failing_tests
                else "Phase 3 decomposition completed with validation failures."
            ),
            "",
            f"The largest exact tie-out gap is `{max_tie_out_gap:.12f}`.",
            f"The largest single factor magnitude in the generated output is `{max_abs_driver:.12f}` log points.",
            "",
            "## Important note",
            "",
            "- The `2001-2025` window is fully decomposed, but the older share-count basis still needs business review before drawing strong conclusions across the 2014 break.",
            "- This phase gives you an exact factor bridge for analysis; it does not yet answer the narrative business questions.",
            "",
            "## Output files",
            "",
            f"- `{ANNUAL_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
            f"- `{DECOMPOSITION_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
            f"- `{VALIDATION_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
            f"- `{SUMMARY_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
        ]
    )

    SUMMARY_OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    all_years = sorted(
        {
            str(year)
            for _, start_year, end_year in WINDOWS
            for year in range(start_year, end_year + 1)
        }
    )
    model_series = load_model_series(all_years)

    annual_rows: List[Dict[str, float]] = []
    decomposition_rows: List[Dict[str, object]] = []

    for window_label, start_year, end_year in WINDOWS:
        years = years_for_window(start_year, end_year)
        window_annual_rows = build_annual_rows(window_label, years, model_series)
        window_decomposition_rows = build_decomposition_rows(
            window_label, window_annual_rows
        )

        annual_rows.extend(window_annual_rows)
        decomposition_rows.extend(window_decomposition_rows)

    validation_rows = build_validation_rows(annual_rows, decomposition_rows)

    write_csv(ANNUAL_OUTPUT_PATH, annual_rows)
    write_csv(DECOMPOSITION_OUTPUT_PATH, decomposition_rows)
    write_csv(VALIDATION_OUTPUT_PATH, validation_rows)
    write_summary(annual_rows, decomposition_rows, validation_rows)

    print(f"Wrote {ANNUAL_OUTPUT_PATH.name}")
    print(f"Wrote {DECOMPOSITION_OUTPUT_PATH.name}")
    print(f"Wrote {VALIDATION_OUTPUT_PATH.name}")
    print(f"Wrote {SUMMARY_OUTPUT_PATH.name}")


if __name__ == "__main__":
    main()
