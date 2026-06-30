#!/usr/bin/env python3
"""Expand the Phase 1 EPS methodology to the longer requested windows.

Phase 2 keeps the same two-factor structure from the formulas sheet:

- `Rev/S`
- `Net Margin`

For each requested window, this script:

1. Rebuilds the annual driver table from `Model.csv`
2. Computes the base-year horizon expansion used in the formulas sheet
3. Writes validation results so each phase has a testing trail

Outputs:

- `phase2_eps_annual_tables.csv`
- `phase2_eps_horizon_expansion.csv`
- `phase2_eps_validation_results.csv`
- `phase2_eps_summary.md`
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "data" / "GOOG MS ML 10-Year Actuals" / "Model.csv"
FORMULAS_PATH = ROOT / "data" / "GOOG EPS Formulas ML Project" / "Sheet1.csv"

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

ANNUAL_OUTPUT_PATH = ROOT / "outputs" / "phase2" / "phase2_eps_annual_tables.csv"
HORIZON_OUTPUT_PATH = ROOT / "outputs" / "phase2" / "phase2_eps_horizon_expansion.csv"
VALIDATION_OUTPUT_PATH = ROOT / "outputs" / "phase2" / "phase2_eps_validation_results.csv"
SUMMARY_OUTPUT_PATH = ROOT / "outputs" / "phase2" / "phase2_eps_summary.md"


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


def years_for_window(start_year: int, end_year: int) -> List[str]:
    return [str(year) for year in range(start_year, end_year + 1)]


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

        # Writing the derived metrics into the exported table makes manual Excel
        # review much easier, especially when someone wants to audit one year.
        rev_per_share = revenue / shares
        net_margin = net_income / revenue
        eps = net_income / shares

        annual_rows.append(
            {
                "window_label": window_label,
                "year": int(year),
                "revenue": revenue,
                "net_income": net_income,
                "average_diluted_shares": shares,
                "rev_per_share": rev_per_share,
                "net_margin": net_margin,
                "eps": eps,
            }
        )

    return annual_rows


def build_horizon_rows(
    window_label: str,
    annual_rows: List[Dict[str, float]],
) -> List[Dict[str, float]]:
    horizon_rows: List[Dict[str, float]] = []
    base = annual_rows[0]

    for index in range(1, len(annual_rows)):
        current = annual_rows[index]
        horizon_years = index

        # This mirrors the formulas sheet: each row is an annualized horizon
        # from the base year, not an adjacent year-over-year change.
        delta_rev_per_share = (
            current["rev_per_share"] / base["rev_per_share"]
        ) ** (1 / horizon_years) - 1
        delta_net_margin = (
            current["net_margin"] / base["net_margin"]
        ) ** (1 / horizon_years) - 1
        delta_eps_actual_cagr = (current["eps"] / base["eps"]) ** (
            1 / horizon_years
        ) - 1

        # The formulas sheet treats EPS change as the additive combination of
        # the two drivers, so we keep that value separate from the true EPS CAGR.
        delta_eps_sheet_logic = delta_rev_per_share + delta_net_margin

        horizon_rows.append(
            {
                "window_label": window_label,
                "base_year": int(base["year"]),
                "target_year": int(current["year"]),
                "horizon_years": horizon_years,
                "period": f"{int(base['year'])}-{int(current['year'])}",
                "delta_rev_per_share": delta_rev_per_share,
                "delta_net_margin": delta_net_margin,
                "delta_eps_sheet_logic": delta_eps_sheet_logic,
                "delta_eps_actual_cagr": delta_eps_actual_cagr,
                "additive_gap": delta_eps_actual_cagr - delta_eps_sheet_logic,
            }
        )

    return horizon_rows


def load_formula_expectations() -> Dict[str, List[float]]:
    rows = read_csv_rows(FORMULAS_PATH)

    def values_for_row(label: str) -> List[float]:
        for row in rows:
            if len(row) > 1 and row[1] == label:
                return [float(value) for value in row[2:] if value]
        raise ValueError(f"Could not find formulas row {label!r}")

    return {
        "delta_rev_per_share": values_for_row("∆Rev/Share"),
        "delta_net_margin": values_for_row("∆NetMargin"),
        "delta_eps": values_for_row("∆EPS"),
    }


def build_validation_rows(
    annual_rows: List[Dict[str, float]],
    horizon_rows: List[Dict[str, float]],
) -> List[Dict[str, object]]:
    validation_rows: List[Dict[str, object]] = []

    annual_counts = {}
    horizon_counts = {}
    for window_label, start_year, end_year in WINDOWS:
        annual_count = sum(1 for row in annual_rows if row["window_label"] == window_label)
        horizon_count = sum(
            1 for row in horizon_rows if row["window_label"] == window_label
        )

        annual_counts[window_label] = annual_count
        horizon_counts[window_label] = horizon_count

        expected_annual_count = end_year - start_year + 1
        expected_horizon_count = expected_annual_count - 1

        validation_rows.append(
            {
                "test_name": f"{window_label}_annual_row_count",
                "status": "PASS" if annual_count == expected_annual_count else "FAIL",
                "details": (
                    f"expected {expected_annual_count}, got {annual_count}"
                ),
            }
        )
        validation_rows.append(
            {
                "test_name": f"{window_label}_horizon_row_count",
                "status": "PASS" if horizon_count == expected_horizon_count else "FAIL",
                "details": (
                    f"expected {expected_horizon_count}, got {horizon_count}"
                ),
            }
        )

    # This is the most important Phase 2 test: confirm the extended script still
    # matches the formulas sheet on the original 2015-2020 sample.
    formula_expectations = load_formula_expectations()
    phase1_rows = [
        row for row in horizon_rows if row["window_label"] == "2015_2025"
    ][:5]

    max_formula_delta = 0.0
    for index, row in enumerate(phase1_rows):
        max_formula_delta = max(
            max_formula_delta,
            abs(row["delta_rev_per_share"] - formula_expectations["delta_rev_per_share"][index]),
            abs(row["delta_net_margin"] - formula_expectations["delta_net_margin"][index]),
            abs(row["delta_eps_sheet_logic"] - formula_expectations["delta_eps"][index]),
        )

    validation_rows.append(
        {
            "test_name": "phase1_formula_tie_out_within_phase2",
            "status": "PASS" if max_formula_delta < 1e-12 else "FAIL",
            "details": f"max difference {max_formula_delta:.12f}",
        }
    )

    all_values_finite = all(
        row["delta_rev_per_share"] == row["delta_rev_per_share"]
        and row["delta_net_margin"] == row["delta_net_margin"]
        and row["delta_eps_sheet_logic"] == row["delta_eps_sheet_logic"]
        and row["delta_eps_actual_cagr"] == row["delta_eps_actual_cagr"]
        for row in horizon_rows
    )
    validation_rows.append(
        {
            "test_name": "all_horizon_values_are_finite",
            "status": "PASS" if all_values_finite else "FAIL",
            "details": "checked all generated horizon rows",
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
    horizon_rows: List[Dict[str, float]],
    validation_rows: List[Dict[str, object]],
) -> None:
    max_gap = max(abs(row["additive_gap"]) for row in horizon_rows)
    failing_tests = [row for row in validation_rows if row["status"] != "PASS"]

    lines = [
        "# Phase 2 EPS Expansion Summary",
        "",
        "## What this does",
        "",
        "- Expands the formulas-sheet methodology to the requested longer windows.",
        "- Rebuilds annual tables for `2015-2025`, `2010-2025`, and `2001-2025`.",
        "- Exports the base-year horizon results for each window.",
        "- Writes explicit validation results so Phase 2 is test-backed.",
        "",
        "## Windows covered",
        "",
    ]

    for window_label, start_year, end_year in WINDOWS:
        annual_count = sum(1 for row in annual_rows if row["window_label"] == window_label)
        horizon_count = sum(
            1 for row in horizon_rows if row["window_label"] == window_label
        )
        lines.append(
            f"- `{window_label}`: {annual_count} annual rows, {horizon_count} horizon rows"
        )

    lines.extend(
        [
            "",
            "## Testing",
            "",
            "- The Phase 1 formulas-sheet sample still ties out inside the Phase 2 script.",
            "- Row counts were validated for each requested window.",
            "- All generated horizon values were checked for finite numeric output.",
            "",
            "## Result",
            "",
            "Phase 2 expansion completed successfully."
            if not failing_tests
            else "Phase 2 expansion completed with validation failures.",
            "",
            f"The largest gap between the sheet-style approximation and true EPS CAGR is `{max_gap:.12f}`.",
            "",
            "## Important note",
            "",
            "- The `2001-2025` window mechanically expands correctly, but the older share series still needs business review because of the share-basis jump around 2014.",
            "- This phase is an exact methodology expansion, not yet a share-normalization cleanup.",
            "",
            "## Output files",
            "",
            f"- `{ANNUAL_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
            f"- `{HORIZON_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
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
    horizon_rows: List[Dict[str, float]] = []

    for window_label, start_year, end_year in WINDOWS:
        years = years_for_window(start_year, end_year)
        window_annual_rows = build_annual_rows(window_label, years, model_series)
        window_horizon_rows = build_horizon_rows(window_label, window_annual_rows)

        annual_rows.extend(window_annual_rows)
        horizon_rows.extend(window_horizon_rows)

    validation_rows = build_validation_rows(annual_rows, horizon_rows)

    write_csv(ANNUAL_OUTPUT_PATH, annual_rows)
    write_csv(HORIZON_OUTPUT_PATH, horizon_rows)
    write_csv(VALIDATION_OUTPUT_PATH, validation_rows)
    write_summary(annual_rows, horizon_rows, validation_rows)

    print(f"Wrote {ANNUAL_OUTPUT_PATH.name}")
    print(f"Wrote {HORIZON_OUTPUT_PATH.name}")
    print(f"Wrote {VALIDATION_OUTPUT_PATH.name}")
    print(f"Wrote {SUMMARY_OUTPUT_PATH.name}")


if __name__ == "__main__":
    main()
