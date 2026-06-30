#!/usr/bin/env python3
"""Answer the Phase 4 EPS business questions.

This phase turns the Phase 2 and Phase 3 calculation outputs into:

1. A year-over-year two-factor bridge for `Rev/S` and `Net Margin`
2. An enriched three-factor table with factor ranking and direction flags
3. A written summary that answers the business questions directly
4. A validation file so Phase 4 is tested like the earlier phases

The script intentionally reads the Phase 3 outputs so the business analysis is
built on the exact factor bridge that already passed validation.
"""

from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parent.parent
PHASE3_ANNUAL_PATH = ROOT / "outputs" / "phase3" / "phase3_eps_annual_tables.csv"
PHASE3_DECOMP_PATH = ROOT / "outputs" / "phase3" / "phase3_eps_three_factor_decomposition.csv"

WINDOWS = ["2015_2025", "2010_2025", "2001_2025"]
ROLLING_WINDOW_LABEL = "2015_2025"
ROLLING_START_YEAR = 2020
ROLLING_END_YEAR = 2025

TWO_FACTOR_OUTPUT_PATH = ROOT / "outputs" / "phase4" / "phase4_eps_two_factor_yoy.csv"
THREE_FACTOR_OUTPUT_PATH = ROOT / "outputs" / "phase4" / "phase4_eps_year_over_year_analysis.csv"
VALIDATION_OUTPUT_PATH = ROOT / "outputs" / "phase4" / "phase4_eps_validation_results.csv"
SUMMARY_OUTPUT_PATH = ROOT / "outputs" / "phase4" / "phase4_eps_business_answers.md"


def read_csv_dicts(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def to_float(value: str) -> float:
    return float(value)


def to_int(value: str) -> int:
    return int(value)


def pearson_correlation(x_values: Sequence[float], y_values: Sequence[float]) -> float:
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


def load_phase3_annual_rows() -> List[Dict[str, float]]:
    rows = read_csv_dicts(PHASE3_ANNUAL_PATH)
    converted: List[Dict[str, float]] = []

    for row in rows:
        converted.append(
            {
                "window_label": row["window_label"],
                "year": to_int(row["year"]),
                "revenue": to_float(row["revenue"]),
                "net_income": to_float(row["net_income"]),
                "average_diluted_shares": to_float(row["average_diluted_shares"]),
                "net_margin": to_float(row["net_margin"]),
                "rev_per_share": to_float(row["rev_per_share"]),
                "eps": to_float(row["eps"]),
            }
        )

    return converted


def load_phase3_decomposition_rows() -> List[Dict[str, float]]:
    rows = read_csv_dicts(PHASE3_DECOMP_PATH)
    converted: List[Dict[str, float]] = []

    for row in rows:
        converted.append(
            {
                "window_label": row["window_label"],
                "from_year": to_int(row["from_year"]),
                "to_year": to_int(row["to_year"]),
                "period": row["period"],
                "revenue_growth": to_float(row["revenue_growth"]),
                "net_margin_growth": to_float(row["net_margin_growth"]),
                "share_count_growth": to_float(row["share_count_growth"]),
                "eps_growth": to_float(row["eps_growth"]),
                "share_count_effect_simple": to_float(row["share_count_effect_simple"]),
                "revenue_log_contribution": to_float(row["revenue_log_contribution"]),
                "net_margin_log_contribution": to_float(row["net_margin_log_contribution"]),
                "share_count_log_contribution": to_float(
                    row["share_count_log_contribution"]
                ),
                "rev_per_share_log_contribution": to_float(
                    row["rev_per_share_log_contribution"]
                ),
                "eps_log_change": to_float(row["eps_log_change"]),
                "tie_out_gap": to_float(row["tie_out_gap"]),
                "largest_driver": row["largest_driver"],
                "largest_driver_direction": row["largest_driver_direction"],
                "largest_driver_abs_log_contribution": to_float(
                    row["largest_driver_abs_log_contribution"]
                ),
            }
        )

    return converted


def build_two_factor_rows(annual_rows: List[Dict[str, float]]) -> List[Dict[str, object]]:
    rows_by_window: Dict[str, List[Dict[str, float]]] = {window: [] for window in WINDOWS}
    for row in annual_rows:
        rows_by_window[row["window_label"]].append(row)

    output_rows: List[Dict[str, object]] = []

    for window_label, rows in rows_by_window.items():
        rows.sort(key=lambda row: row["year"])

        for index in range(1, len(rows)):
            previous = rows[index - 1]
            current = rows[index]

            # This is the exact two-factor bridge for the question:
            # EPS = Rev/S x Net Margin.
            rev_per_share_log_contribution = math.log(
                current["rev_per_share"] / previous["rev_per_share"]
            )
            net_margin_log_contribution = math.log(
                current["net_margin"] / previous["net_margin"]
            )
            eps_log_change = math.log(current["eps"] / previous["eps"])

            output_rows.append(
                {
                    "window_label": window_label,
                    "from_year": previous["year"],
                    "to_year": current["year"],
                    "period": f"{previous['year']}-{current['year']}",
                    "delta_rev_per_share_growth": (
                        current["rev_per_share"] / previous["rev_per_share"] - 1
                    ),
                    "delta_net_margin_growth": (
                        current["net_margin"] / previous["net_margin"] - 1
                    ),
                    "delta_eps_growth": current["eps"] / previous["eps"] - 1,
                    "rev_per_share_log_contribution": rev_per_share_log_contribution,
                    "net_margin_log_contribution": net_margin_log_contribution,
                    "eps_log_change": eps_log_change,
                    "two_factor_tie_out_gap": (
                        eps_log_change
                        - (
                            rev_per_share_log_contribution
                            + net_margin_log_contribution
                        )
                    ),
                    "dominant_two_factor": (
                        "rev_per_share"
                        if abs(rev_per_share_log_contribution)
                        >= abs(net_margin_log_contribution)
                        else "net_margin"
                    ),
                }
            )

    return output_rows


def rank_factors(row: Dict[str, float]) -> List[Tuple[str, float]]:
    factor_items = [
        ("revenue", row["revenue_log_contribution"]),
        ("net_margin", row["net_margin_log_contribution"]),
        ("share_count", row["share_count_log_contribution"]),
    ]
    return sorted(factor_items, key=lambda item: abs(item[1]), reverse=True)


def build_three_factor_analysis_rows(
    decomposition_rows: List[Dict[str, float]]
) -> List[Dict[str, object]]:
    analysis_rows: List[Dict[str, object]] = []

    for row in decomposition_rows:
        ranked = rank_factors(row)
        has_offsetting_factors = (
            any(value > 0 for _, value in ranked)
            and any(value < 0 for _, value in ranked)
        )

        analysis_rows.append(
            {
                **row,
                "rank_1_factor": ranked[0][0],
                "rank_1_log_contribution": ranked[0][1],
                "rank_2_factor": ranked[1][0],
                "rank_2_log_contribution": ranked[1][1],
                "rank_3_factor": ranked[2][0],
                "rank_3_log_contribution": ranked[2][1],
                "has_offsetting_factors": "yes" if has_offsetting_factors else "no",
                "eps_direction": (
                    "positive"
                    if row["eps_growth"] > 0
                    else "negative"
                    if row["eps_growth"] < 0
                    else "flat"
                ),
            }
        )

    return analysis_rows


def full_window_rows(
    rows: Iterable[Dict[str, float]],
    window_label: str = "2001_2025",
) -> List[Dict[str, float]]:
    return [row for row in rows if row["window_label"] == window_label]


def rolling_rows(rows: Iterable[Dict[str, float]]) -> List[Dict[str, float]]:
    return [
        row
        for row in rows
        if row["window_label"] == ROLLING_WINDOW_LABEL
        and row["from_year"] >= ROLLING_START_YEAR
        and row["to_year"] <= ROLLING_END_YEAR
    ]


def factor_stats(rows: List[Dict[str, float]], factor_key: str) -> Dict[str, float]:
    values = [row[factor_key] for row in rows]
    return {
        "positive_count": sum(1 for value in values if value > 0),
        "mean": statistics.fmean(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def format_float(value: float) -> str:
    if math.isnan(value):
        return "N/A"
    return f"{value:.4f}"


def build_validation_rows(
    annual_rows: List[Dict[str, float]],
    two_factor_rows: List[Dict[str, object]],
    three_factor_rows: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    validation_rows: List[Dict[str, object]] = []

    for window_label in WINDOWS:
        annual_count = sum(1 for row in annual_rows if row["window_label"] == window_label)
        two_factor_count = sum(
            1 for row in two_factor_rows if row["window_label"] == window_label
        )
        three_factor_count = sum(
            1 for row in three_factor_rows if row["window_label"] == window_label
        )
        expected_count = annual_count - 1

        validation_rows.append(
            {
                "test_name": f"{window_label}_two_factor_row_count",
                "status": "PASS" if two_factor_count == expected_count else "FAIL",
                "details": f"expected {expected_count}, got {two_factor_count}",
            }
        )
        validation_rows.append(
            {
                "test_name": f"{window_label}_three_factor_row_count",
                "status": "PASS" if three_factor_count == expected_count else "FAIL",
                "details": f"expected {expected_count}, got {three_factor_count}",
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

    ranking_complete = all(
        row["rank_1_factor"] != row["rank_2_factor"]
        and row["rank_2_factor"] != row["rank_3_factor"]
        and row["rank_1_factor"] != row["rank_3_factor"]
        for row in three_factor_rows
    )
    validation_rows.append(
        {
            "test_name": "three_factor_ranking_complete",
            "status": "PASS" if ranking_complete else "FAIL",
            "details": "rank columns contain three distinct factors",
        }
    )

    rolling_periods = rolling_rows(three_factor_rows)
    validation_rows.append(
        {
            "test_name": "rolling_window_has_expected_periods",
            "status": "PASS" if len(rolling_periods) == 5 else "FAIL",
            "details": f"expected 5, got {len(rolling_periods)}",
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
    two_factor_rows: List[Dict[str, object]],
    three_factor_rows: List[Dict[str, object]],
    validation_rows: List[Dict[str, object]],
) -> None:
    failing_tests = [row for row in validation_rows if row["status"] != "PASS"]
    full_rows = full_window_rows(three_factor_rows)
    rolling = rolling_rows(three_factor_rows)

    largest_swing = max(full_rows, key=lambda row: abs(row["largest_driver_abs_log_contribution"]))

    rolling_factor_map = {
        "revenue": "revenue_log_contribution",
        "net_margin": "net_margin_log_contribution",
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
    most_volatile = max(
        rolling_stats.items(),
        key=lambda item: item[1]["stdev"],
    )[0]

    offsetting_rolling_periods = [
        row["period"] for row in rolling if row["has_offsetting_factors"] == "yes"
    ]

    revenue_growth_values = [row["revenue_growth"] for row in full_rows]
    significant_threshold = statistics.quantiles(
        revenue_growth_values, n=4, method="inclusive"
    )[2]
    significant_revenue_rows = [
        row for row in full_rows if row["revenue_growth"] >= significant_threshold
    ]
    significant_expand = sum(1 for row in significant_revenue_rows if row["net_margin_growth"] > 0)
    significant_contract = sum(
        1 for row in significant_revenue_rows if row["net_margin_growth"] < 0
    )
    significant_flat = len(significant_revenue_rows) - significant_expand - significant_contract
    revenue_margin_corr = pearson_correlation(
        [row["revenue_growth"] for row in full_rows],
        [row["net_margin_growth"] for row in full_rows],
    )

    margin_down_eps_up_rows = [
        row
        for row in full_rows
        if row["net_margin_growth"] < 0 and row["eps_growth"] > 0
    ]
    revenue_enough_rows = [
        row
        for row in margin_down_eps_up_rows
        if row["revenue_log_contribution"]
        > abs(
            row["net_margin_log_contribution"] + row["share_count_log_contribution"]
        )
    ]

    buyback_rows = [row for row in full_rows if row["share_count_growth"] < 0]
    buyback_rev_corr = pearson_correlation(
        [row["share_count_log_contribution"] for row in buyback_rows],
        [row["revenue_log_contribution"] for row in buyback_rows],
    )
    buyback_margin_corr = pearson_correlation(
        [row["share_count_log_contribution"] for row in buyback_rows],
        [row["net_margin_log_contribution"] for row in buyback_rows],
    )

    lines = [
        "# Phase 4 EPS Business Analysis",
        "",
        "## Testing",
        "",
        (
            "All Phase 4 validation checks passed."
            if not failing_tests
            else "Phase 4 completed with validation failures."
        ),
        "",
        "Validation file:",
        f"- `{VALIDATION_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
        "",
        "## Replication And Expansion",
        "",
        "The exact year-over-year two-factor bridge is exported in `outputs/phase4/phase4_eps_two_factor_yoy.csv`.",
        "For each requested window, that file shows how `Rev/S` and `Net Margin` contributed to EPS movement for every adjacent year pair.",
        "",
        "The enriched three-factor year-over-year file is `outputs/phase4/phase4_eps_year_over_year_analysis.csv`.",
        "It adds factor ranks, direction labels, and offset flags for each period.",
        "",
        "## Year-Over-Year Decomposition",
        "",
        f"The single largest factor swing in the full `2001-2025` output is `{largest_swing['largest_driver']}` in `{largest_swing['period']}`, and it is `{largest_swing['largest_driver_direction']}`.",
        "Diluted shares are now on a consistent split-adjusted basis (pre-split 2001-2013 restated x20), so this swing is no longer distorted by the old data break.",
        "",
        "## Five-Year Rolling Analysis",
        "",
        f"Using the `2020-2025` year-over-year periods, the most consistent positive contributor is `{most_consistent}`.",
        f"The most volatile factor over the same periods is `{most_volatile}`.",
        f"Offsetting factor moves occurred in: `{', '.join(offsetting_rolling_periods)}`.",
        "",
        "Five-year rolling factor stats:",
        f"- `revenue`: positive in {rolling_stats['revenue']['positive_count']} of 5 periods, stdev `{format_float(rolling_stats['revenue']['stdev'])}`",
        f"- `net_margin`: positive in {rolling_stats['net_margin']['positive_count']} of 5 periods, stdev `{format_float(rolling_stats['net_margin']['stdev'])}`",
        f"- `share_count`: positive in {rolling_stats['share_count']['positive_count']} of 5 periods, stdev `{format_float(rolling_stats['share_count']['stdev'])}`",
        "",
        "## Correlation And Relationships",
        "",
        f"Across the full `2001-2025` year-over-year dataset, the correlation between revenue growth and net-margin change is `{format_float(revenue_margin_corr)}`.",
        f"For the top-quartile revenue-growth years (threshold `{format_float(significant_threshold)}`), net margin expanded in `{significant_expand}` periods, contracted in `{significant_contract}`, and was flat in `{significant_flat}`.",
        "",
        f"When net margin contracted, EPS still rose in `{len(margin_down_eps_up_rows)}` periods.",
        f"In `{len(revenue_enough_rows)}` of those periods, revenue contribution alone outweighed the combined drag from margin and shares.",
        "",
        f"For years with falling share count, the buyback contribution correlates `{format_float(buyback_rev_corr)}` with revenue contribution and `{format_float(buyback_margin_corr)}` with net-margin contribution.",
        (
            "That means the share-count lift aligns more strongly with revenue than margin."
            if abs(buyback_rev_corr) > abs(buyback_margin_corr)
            else "That means the share-count lift aligns more strongly with net margin than revenue."
        ),
        "",
        "## Output Files",
        "",
        f"- `{TWO_FACTOR_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
        f"- `{THREE_FACTOR_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
        f"- `{VALIDATION_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
        f"- `{SUMMARY_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
        "",
        "## Important Note",
        "",
        "- The pre-split 2001-2013 diluted-share counts have been restated x20, so the share series is consistent across the full history.",
        "- The Phase 4 answers are mechanically correct and long-run share-count conclusions no longer require a split-normalization caveat.",
    ]

    SUMMARY_OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    annual_rows = load_phase3_annual_rows()
    decomposition_rows = load_phase3_decomposition_rows()

    two_factor_rows = build_two_factor_rows(annual_rows)
    three_factor_rows = build_three_factor_analysis_rows(decomposition_rows)
    validation_rows = build_validation_rows(
        annual_rows, two_factor_rows, three_factor_rows
    )

    write_csv(TWO_FACTOR_OUTPUT_PATH, two_factor_rows)
    write_csv(THREE_FACTOR_OUTPUT_PATH, three_factor_rows)
    write_csv(VALIDATION_OUTPUT_PATH, validation_rows)
    write_summary(two_factor_rows, three_factor_rows, validation_rows)

    print(f"Wrote {TWO_FACTOR_OUTPUT_PATH.name}")
    print(f"Wrote {THREE_FACTOR_OUTPUT_PATH.name}")
    print(f"Wrote {VALIDATION_OUTPUT_PATH.name}")
    print(f"Wrote {SUMMARY_OUTPUT_PATH.name}")


if __name__ == "__main__":
    main()
