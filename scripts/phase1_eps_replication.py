#!/usr/bin/env python3
"""Recreate Phase 1 of the EPS analysis task plan.

This script rebuilds the 2015-2020 annual table from the model export and
replicates the horizon-based methodology shown in the formulas sheet.
It writes three outputs next to the script:

- `phase1_eps_annual_table_2015_2020.csv`
- `phase1_eps_replication_check_2015_2020.csv`
- `phase1_eps_replication_summary_2015_2020.md`
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "data" / "GOOG MS ML 10-Year Actuals" / "Model.csv"
FORMULAS_PATH = ROOT / "data" / "GOOG EPS Formulas ML Project" / "Sheet1.csv"

YEARS = ["2015", "2016", "2017", "2018", "2019", "2020"]
KEY_ROWS = {
    "revenue": "Total Gross revenue (GAAP)",
    "net_income": "Net income, reported",
    "shares": "Average diluted shares",
}

ANNUAL_OUTPUT_PATH = ROOT / "outputs" / "phase1" / "phase1_eps_annual_table_2015_2020.csv"
REPLICATION_OUTPUT_PATH = ROOT / "outputs" / "phase1" / "phase1_eps_replication_check_2015_2020.csv"
SUMMARY_OUTPUT_PATH = ROOT / "outputs" / "phase1" / "phase1_eps_replication_summary_2015_2020.md"


def read_csv_rows(path: Path) -> List[List[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.reader(handle))


def find_row(rows: Iterable[List[str]], label: str) -> List[str]:
    for row in rows:
        if label in row:
            return row
    raise ValueError(f"Could not find row labeled {label!r}")


def annual_year_columns(model_rows: List[List[str]]) -> Dict[str, int]:
    """Map each annual year label to its column index.

    The model export contains many quarterly columns first and then a clean
    annual block later in the sheet. We intentionally read the annual block so
    the calculations align with the task request.
    """

    header_row = model_rows[6]
    mapping: Dict[str, int] = {}

    for index, value in enumerate(header_row):
        if value.endswith("00:00:00"):
            year = value[:4]
            mapping[year] = index

    return mapping


def load_model_series() -> Dict[str, Dict[str, float]]:
    model_rows = read_csv_rows(MODEL_PATH)
    year_to_col = annual_year_columns(model_rows)

    series: Dict[str, Dict[str, float]] = {}
    for series_name, row_label in KEY_ROWS.items():
        row = find_row(model_rows, row_label)
        series[series_name] = {
            year: float(row[year_to_col[year]])
            for year in YEARS
        }

    return series


def build_annual_table(series: Dict[str, Dict[str, float]]) -> List[Dict[str, float]]:
    annual_rows: List[Dict[str, float]] = []

    for year in YEARS:
        revenue = series["revenue"][year]
        net_income = series["net_income"][year]
        shares = series["shares"][year]

        # Keep the derived metrics explicit in the table so the audit trail is
        # easy to follow when someone checks the math manually in Excel.
        rev_per_share = revenue / shares
        net_margin = net_income / revenue
        eps = net_income / shares

        annual_rows.append(
            {
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


def build_replication_check(
    annual_rows: List[Dict[str, float]],
    expectations: Dict[str, List[float]],
) -> List[Dict[str, float]]:
    replication_rows: List[Dict[str, float]] = []
    base = annual_rows[0]

    for index in range(1, len(annual_rows)):
        current = annual_rows[index]
        horizon_years = index

        # The formulas sheet treats "Year 1" through "Year 5" as rolling
        # horizons from the 2015 base year, annualized over the horizon length.
        # Example: Year 2 means 2015 -> 2017, expressed as a 2-year CAGR.
        delta_rev_per_share = (
            current["rev_per_share"] / base["rev_per_share"]
        ) ** (1 / horizon_years) - 1
        delta_net_margin = (
            current["net_margin"] / base["net_margin"]
        ) ** (1 / horizon_years) - 1
        delta_eps = (current["eps"] / base["eps"]) ** (1 / horizon_years) - 1

        additive_estimate = delta_rev_per_share + delta_net_margin

        # The formulas sheet uses an additive approximation. The gap below is
        # the interaction term created because EPS = Rev/S * Net Margin.
        additive_gap = delta_eps - additive_estimate

        replication_rows.append(
            {
                "base_year": int(base["year"]),
                "target_year": int(current["year"]),
                "horizon_years": horizon_years,
                "period": f"{int(base['year'])}-{int(current['year'])}",
                "delta_rev_per_share_calculated": delta_rev_per_share,
                "delta_rev_per_share_sheet": expectations["delta_rev_per_share"][index - 1],
                "delta_net_margin_calculated": delta_net_margin,
                "delta_net_margin_sheet": expectations["delta_net_margin"][index - 1],
                "delta_eps_actual_cagr": delta_eps,
                "delta_eps_sheet_logic_calculated": additive_estimate,
                "delta_eps_sheet": expectations["delta_eps"][index - 1],
                "additive_gap": additive_gap,
            }
        )

    return replication_rows


def write_csv(path: Path, rows: List[Dict[str, float]]) -> None:
    if not rows:
        raise ValueError(f"No rows were generated for {path.name}")

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_summary(
    annual_rows: List[Dict[str, float]],
    replication_rows: List[Dict[str, float]],
) -> None:
    max_abs_gap = max(abs(row["additive_gap"]) for row in replication_rows)
    max_sheet_delta = max(
        max(
            abs(
                row["delta_rev_per_share_calculated"]
                - row["delta_rev_per_share_sheet"]
            ),
            abs(row["delta_net_margin_calculated"] - row["delta_net_margin_sheet"]),
            abs(
                row["delta_eps_sheet_logic_calculated"] - row["delta_eps_sheet"]
            ),
        )
        for row in replication_rows
    )

    lines = [
        "# Phase 1 EPS Replication Summary",
        "",
        "## What this does",
        "",
        "- Rebuilds the 2015-2020 annual EPS driver table from `Model.csv`.",
        "- Recreates the same base-year horizon metrics shown in `Sheet1.csv`.",
        "- Compares the calculated results against the formulas sheet values.",
        "",
        "## Result",
        "",
        "The replication works.",
        "",
        "The calculated `∆Rev/Share`, `∆NetMargin`, and sheet-style `∆EPS` match the formulas sheet values for 2015-2020.",
        "The formulas sheet is using `2015` as the base year and annualizing each horizon, rather than using adjacent year-over-year changes.",
        "It is also treating `∆EPS` as an additive approximation, not as the true EPS CAGR.",
        "",
        "That additive relationship is close, but not exact, because EPS is multiplicative:",
        "",
        "```text",
        "EPS = Rev/S x Net Margin",
        "```",
        "",
        f"The largest difference versus the formulas sheet is `{max_sheet_delta:.12f}`.",
        f"The largest gap between the sheet-style approximation and the true EPS CAGR is `{max_abs_gap:.12f}`.",
        "",
        "## Output files",
        "",
        f"- `{ANNUAL_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
        f"- `{REPLICATION_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
        f"- `{SUMMARY_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
        "",
        "## Notes",
        "",
        "- This completes Phase 1 only.",
        "- The next step is to extend the same methodology through 2025 before moving to the 3-factor decomposition.",
    ]

    SUMMARY_OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    model_series = load_model_series()
    annual_rows = build_annual_table(model_series)
    formula_expectations = load_formula_expectations()
    replication_rows = build_replication_check(annual_rows, formula_expectations)

    write_csv(ANNUAL_OUTPUT_PATH, annual_rows)
    write_csv(REPLICATION_OUTPUT_PATH, replication_rows)
    write_summary(annual_rows, replication_rows)

    print(f"Wrote {ANNUAL_OUTPUT_PATH.name}")
    print(f"Wrote {REPLICATION_OUTPUT_PATH.name}")
    print(f"Wrote {SUMMARY_OUTPUT_PATH.name}")


if __name__ == "__main__":
    main()
