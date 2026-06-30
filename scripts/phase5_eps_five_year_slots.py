#!/usr/bin/env python3
"""Build the Phase 5 five-year slot view of the EPS decomposition.

Phase 5 reuses the annual driver table produced by Phase 3 and collapses the
long history into non-overlapping five-year slots. For each slot, the script
reports:

- Level values at the slot endpoints (revenue, net income, shares, margin,
  Rev/S, EPS)
- Slot totals (cumulative revenue and net income)
- Slot-level changes (total growth and CAGR for revenue, Rev/S, and EPS)
- The exact two-factor log bridge (`EPS = Rev/S x Net Margin`)
- The exact three-factor log bridge (`EPS = Revenue x Net Margin / Shares`)
- Factor ranking and direction labels for the slot

A second file is produced alongside the slot summary that contains the
year-over-year rows inside each slot, so the slot number can be drilled down
to the underlying year-by-year movement.

Outputs:

- `phase5_eps_five_year_slots.csv`
- `phase5_eps_five_year_slot_breakdown.csv`
- `phase5_eps_five_year_slots_validation.csv`
- `phase5_eps_five_year_slots_summary.md`
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parent.parent
PHASE3_ANNUAL_PATH = ROOT / "outputs" / "phase3" / "phase3_eps_annual_tables.csv"
PHASE4_TWO_FACTOR_PATH = ROOT / "outputs" / "phase4" / "phase4_eps_two_factor_yoy.csv"
PHASE4_THREE_FACTOR_PATH = (
    ROOT / "outputs" / "phase4" / "phase4_eps_year_over_year_analysis.csv"
)

SLOT_OUTPUT_PATH = ROOT / "outputs" / "phase5" / "phase5_eps_five_year_slots.csv"
BREAKDOWN_OUTPUT_PATH = (
    ROOT / "outputs" / "phase5" / "phase5_eps_five_year_slot_breakdown.csv"
)
VALIDATION_OUTPUT_PATH = (
    ROOT / "outputs" / "phase5" / "phase5_eps_five_year_slots_validation.csv"
)
SUMMARY_OUTPUT_PATH = (
    ROOT / "outputs" / "phase5" / "phase5_eps_five_year_slots_summary.md"
)


# Slots are anchored on milestone years so they line up across windows.
# Endpoints are shared between adjacent slots so the totals connect cleanly.
# The 2001-2005 slot is 4 years long because 2001 is not on the 5-year grid;
# every other slot is a full 5-year span.
WINDOW_SLOTS: List[Tuple[str, List[Tuple[int, int]]]] = [
    (
        "2015_2025",
        [(2015, 2020), (2020, 2025)],
    ),
    (
        "2010_2025",
        [(2010, 2015), (2015, 2020), (2020, 2025)],
    ),
    (
        "2001_2025",
        [(2001, 2005), (2005, 2010), (2010, 2015), (2015, 2020), (2020, 2025)],
    ),
]


def read_csv_dicts(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_annual_rows() -> Dict[Tuple[str, int], Dict[str, float]]:
    raw_rows = read_csv_dicts(PHASE3_ANNUAL_PATH)
    annual_rows: Dict[Tuple[str, int], Dict[str, float]] = {}

    for raw in raw_rows:
        key = (raw["window_label"], int(raw["year"]))
        annual_rows[key] = {
            "window_label": raw["window_label"],
            "year": int(raw["year"]),
            "revenue": float(raw["revenue"]),
            "net_income": float(raw["net_income"]),
            "average_diluted_shares": float(raw["average_diluted_shares"]),
            "net_margin": float(raw["net_margin"]),
            "rev_per_share": float(raw["rev_per_share"]),
            "eps": float(raw["eps"]),
        }

    return annual_rows


def get_annual_rows_for_window(
    annual_rows: Dict[Tuple[str, int], Dict[str, float]],
    window_label: str,
    start_year: int,
    end_year: int,
) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    for year in range(start_year, end_year + 1):
        row = annual_rows.get((window_label, year))
        if row is None:
            raise ValueError(
                f"Missing annual row for {window_label} {year}"
                " (expected in phase3_eps_annual_tables.csv)"
            )
        rows.append(row)
    return rows


def cagr(end_value: float, start_value: float, years: int) -> float:
    if years <= 0:
        return 0.0
    return (end_value / start_value) ** (1 / years) - 1


def rank_factors(
    contributions: Dict[str, float],
) -> List[Tuple[str, float]]:
    return sorted(contributions.items(), key=lambda item: abs(item[1]), reverse=True)


def direction_label(value: float) -> str:
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "flat"


def build_slot_rows(
    annual_rows: Dict[Tuple[str, int], Dict[str, float]],
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    slot_rows: List[Dict[str, object]] = []
    breakdown_rows: List[Dict[str, object]] = []

    for window_label, slots in WINDOW_SLOTS:
        for start_year, end_year in slots:
            slot_label = f"{start_year}-{end_year}"
            window_rows = get_annual_rows_for_window(
                annual_rows, window_label, start_year, end_year
            )
            start_row = window_rows[0]
            end_row = window_rows[-1]
            years_in_slot = end_year - start_year

            # Cumulative totals cover every calendar year inside the slot so
            # the dollar figures read as "5-year totals" rather than endpoints.
            revenue_total = sum(row["revenue"] for row in window_rows)
            net_income_total = sum(row["net_income"] for row in window_rows)

            revenue_total_growth = end_row["revenue"] / start_row["revenue"] - 1
            rev_per_share_total_growth = (
                end_row["rev_per_share"] / start_row["rev_per_share"] - 1
            )
            net_margin_total_growth = (
                end_row["net_margin"] / start_row["net_margin"] - 1
            )
            share_count_total_growth = (
                end_row["average_diluted_shares"]
                / start_row["average_diluted_shares"]
                - 1
            )
            eps_total_growth = end_row["eps"] / start_row["eps"] - 1

            revenue_cagr = cagr(end_row["revenue"], start_row["revenue"], years_in_slot)
            rev_per_share_cagr = cagr(
                end_row["rev_per_share"], start_row["rev_per_share"], years_in_slot
            )
            eps_cagr = cagr(end_row["eps"], start_row["eps"], years_in_slot)

            # The two-factor bridge is EPS = Rev/S x Net Margin, so the log of
            # the EPS ratio splits exactly into these two log contributions.
            rev_per_share_log_contribution = math.log(
                end_row["rev_per_share"] / start_row["rev_per_share"]
            )
            net_margin_log_contribution = math.log(
                end_row["net_margin"] / start_row["net_margin"]
            )

            # The three-factor bridge is EPS = Revenue x Net Margin / Shares.
            # Share count contribution flips sign so buybacks read as positive.
            revenue_log_contribution = math.log(
                end_row["revenue"] / start_row["revenue"]
            )
            share_count_log_contribution = -math.log(
                end_row["average_diluted_shares"]
                / start_row["average_diluted_shares"]
            )

            eps_log_change = math.log(end_row["eps"] / start_row["eps"])

            two_factor_tie_out_gap = eps_log_change - (
                rev_per_share_log_contribution + net_margin_log_contribution
            )
            three_factor_tie_out_gap = eps_log_change - (
                revenue_log_contribution
                + net_margin_log_contribution
                + share_count_log_contribution
            )

            two_factor_contributions = {
                "rev_per_share": rev_per_share_log_contribution,
                "net_margin": net_margin_log_contribution,
            }
            three_factor_contributions = {
                "revenue": revenue_log_contribution,
                "net_margin": net_margin_log_contribution,
                "share_count": share_count_log_contribution,
            }

            ranked_two = rank_factors(two_factor_contributions)
            ranked_three = rank_factors(three_factor_contributions)

            dominant_two_factor = ranked_two[0][0]
            dominant_three_factor = ranked_three[0][0]
            dominant_three_factor_direction = direction_label(ranked_three[0][1])
            eps_direction = direction_label(eps_log_change)

            slot_rows.append(
                {
                    "window_label": window_label,
                    "slot": slot_label,
                    "start_year": start_year,
                    "end_year": end_year,
                    "years_in_slot": years_in_slot,
                    "revenue_start": start_row["revenue"],
                    "revenue_end": end_row["revenue"],
                    "revenue_total_in_slot": revenue_total,
                    "revenue_total_growth": revenue_total_growth,
                    "revenue_cagr": revenue_cagr,
                    "net_income_start": start_row["net_income"],
                    "net_income_end": end_row["net_income"],
                    "net_income_total_in_slot": net_income_total,
                    "shares_start": start_row["average_diluted_shares"],
                    "shares_end": end_row["average_diluted_shares"],
                    "share_count_total_growth": share_count_total_growth,
                    "net_margin_start": start_row["net_margin"],
                    "net_margin_end": end_row["net_margin"],
                    "net_margin_total_growth": net_margin_total_growth,
                    "rev_per_share_start": start_row["rev_per_share"],
                    "rev_per_share_end": end_row["rev_per_share"],
                    "rev_per_share_total_growth": rev_per_share_total_growth,
                    "rev_per_share_cagr": rev_per_share_cagr,
                    "eps_start": start_row["eps"],
                    "eps_end": end_row["eps"],
                    "eps_total_growth": eps_total_growth,
                    "eps_cagr": eps_cagr,
                    "rev_per_share_log_contribution": rev_per_share_log_contribution,
                    "net_margin_log_contribution": net_margin_log_contribution,
                    "revenue_log_contribution": revenue_log_contribution,
                    "share_count_log_contribution": share_count_log_contribution,
                    "eps_log_change": eps_log_change,
                    "two_factor_tie_out_gap": two_factor_tie_out_gap,
                    "three_factor_tie_out_gap": three_factor_tie_out_gap,
                    "dominant_two_factor": dominant_two_factor,
                    "dominant_three_factor": dominant_three_factor,
                    "dominant_three_factor_direction": dominant_three_factor_direction,
                    "eps_direction": eps_direction,
                    "rank_1_factor": ranked_three[0][0],
                    "rank_1_log_contribution": ranked_three[0][1],
                    "rank_2_factor": ranked_three[1][0],
                    "rank_2_log_contribution": ranked_three[1][1],
                    "rank_3_factor": ranked_three[2][0],
                    "rank_3_log_contribution": ranked_three[2][1],
                }
            )

            # Drill-down rows: the adjacent year pairs that sit inside the slot.
            for index in range(1, len(window_rows)):
                previous = window_rows[index - 1]
                current = window_rows[index]

                yoy_rev_per_share_log = math.log(
                    current["rev_per_share"] / previous["rev_per_share"]
                )
                yoy_net_margin_log = math.log(
                    current["net_margin"] / previous["net_margin"]
                )
                yoy_revenue_log = math.log(current["revenue"] / previous["revenue"])
                yoy_share_count_log = -math.log(
                    current["average_diluted_shares"]
                    / previous["average_diluted_shares"]
                )
                yoy_eps_log = math.log(current["eps"] / previous["eps"])

                breakdown_rows.append(
                    {
                        "window_label": window_label,
                        "slot": slot_label,
                        "from_year": previous["year"],
                        "to_year": current["year"],
                        "period": f"{previous['year']}-{current['year']}",
                        "revenue_log_contribution": yoy_revenue_log,
                        "net_margin_log_contribution": yoy_net_margin_log,
                        "share_count_log_contribution": yoy_share_count_log,
                        "rev_per_share_log_contribution": yoy_rev_per_share_log,
                        "eps_log_change": yoy_eps_log,
                    }
                )

    return slot_rows, breakdown_rows


def build_validation_rows(
    slot_rows: List[Dict[str, object]],
    breakdown_rows: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    validation_rows: List[Dict[str, object]] = []

    max_two_factor_gap = max(
        abs(float(row["two_factor_tie_out_gap"])) for row in slot_rows
    )
    validation_rows.append(
        {
            "test_name": "two_factor_log_bridge_tie_out",
            "status": "PASS" if max_two_factor_gap < 1e-9 else "FAIL",
            "details": f"max gap {max_two_factor_gap:.12f}",
        }
    )

    max_three_factor_gap = max(
        abs(float(row["three_factor_tie_out_gap"])) for row in slot_rows
    )
    validation_rows.append(
        {
            "test_name": "three_factor_log_bridge_tie_out",
            "status": "PASS" if max_three_factor_gap < 1e-9 else "FAIL",
            "details": f"max gap {max_three_factor_gap:.12f}",
        }
    )

    # Each slot's log change should equal the sum of its inner YoY log changes.
    max_breakdown_gap = 0.0
    for slot_row in slot_rows:
        matching = [
            row
            for row in breakdown_rows
            if row["window_label"] == slot_row["window_label"]
            and row["slot"] == slot_row["slot"]
        ]
        if not matching:
            continue
        summed = sum(float(row["eps_log_change"]) for row in matching)
        gap = abs(summed - float(slot_row["eps_log_change"]))
        if gap > max_breakdown_gap:
            max_breakdown_gap = gap
    validation_rows.append(
        {
            "test_name": "slot_breakdown_matches_slot_total",
            "status": "PASS" if max_breakdown_gap < 1e-9 else "FAIL",
            "details": f"max gap {max_breakdown_gap:.12f}",
        }
    )

    for window_label, slots in WINDOW_SLOTS:
        expected = len(slots)
        actual = sum(1 for row in slot_rows if row["window_label"] == window_label)
        validation_rows.append(
            {
                "test_name": f"{window_label}_slot_count",
                "status": "PASS" if expected == actual else "FAIL",
                "details": f"expected {expected}, got {actual}",
            }
        )

    return validation_rows


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows were generated for {path.name}")

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def format_pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def write_summary(
    slot_rows: List[Dict[str, object]],
    validation_rows: List[Dict[str, object]],
) -> None:
    failing = [row for row in validation_rows if row["status"] != "PASS"]

    lines: List[str] = [
        "# Phase 5 Five-Year Slot Summary",
        "",
        "## What this does",
        "",
        "- Collapses the long history into non-overlapping 5-year slots.",
        "- Reports slot-level totals, endpoint-to-endpoint growth, and CAGR.",
        "- Applies the same log-based 2-factor and 3-factor bridges used in Phase 4.",
        "- Keeps the drill-down year-over-year rows so each slot can be expanded.",
        "",
        "## Slot definition",
        "",
        "- `2015_2025`: 2015-2020, 2020-2025",
        "- `2010_2025`: 2010-2015, 2015-2020, 2020-2025",
        "- `2001_2025`: 2001-2005, 2005-2010, 2010-2015, 2015-2020, 2020-2025",
        "",
        "The `2001-2005` slot covers 4 calendar years because 2001 is not on the 5-year grid.",
        "All other slots are exact 5-year spans.",
        "",
        "## Testing",
        "",
        (
            "All Phase 5 validation checks passed."
            if not failing
            else "Phase 5 completed with validation failures."
        ),
        "",
    ]

    for window_label, slots in WINDOW_SLOTS:
        lines.append(f"### {window_label}")
        lines.append("")
        lines.append(
            "| Slot | Revenue CAGR | EPS CAGR | Rev/S Contribution | Net Margin Contribution | Share Count Contribution | EPS Log Change | Largest Driver | Direction |"
        )
        lines.append(
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"
        )
        for slot_row in slot_rows:
            if slot_row["window_label"] != window_label:
                continue
            lines.append(
                "| {slot} | {rev_cagr} | {eps_cagr} | {rps} | {nm} | {sc} | {eps_log} | {driver} | {direction} |".format(
                    slot=slot_row["slot"],
                    rev_cagr=format_pct(float(slot_row["revenue_cagr"])),
                    eps_cagr=format_pct(float(slot_row["eps_cagr"])),
                    rps=f"{float(slot_row['rev_per_share_log_contribution']):.4f}",
                    nm=f"{float(slot_row['net_margin_log_contribution']):.4f}",
                    sc=f"{float(slot_row['share_count_log_contribution']):.4f}",
                    eps_log=f"{float(slot_row['eps_log_change']):.4f}",
                    driver=slot_row["dominant_three_factor"],
                    direction=slot_row["dominant_three_factor_direction"],
                )
            )
        lines.append("")

    lines.extend(
        [
            "## Notes",
            "",
            "- Positive log contribution = that factor helped EPS in the slot.",
            "- Negative log contribution = that factor hurt EPS in the slot.",
            "- `share_count` is signed so buybacks read as positive.",
            "- Diluted shares are on a consistent split-adjusted basis (pre-split 2001-2013 restated x20), so the old 2013-2014 break no longer distorts the `2010-2015` slot.",
            "- Adjacent slots share one endpoint year so the log contributions connect cleanly; as a result, `revenue_total_in_slot` and `net_income_total_in_slot` double-count that endpoint if summed across slots.",
            "- Use the breakdown CSV for the year-by-year view that sums to each slot total.",
            "",
            "## Output files",
            "",
            f"- `{SLOT_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
            f"- `{BREAKDOWN_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
            f"- `{VALIDATION_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
            f"- `{SUMMARY_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
        ]
    )

    SUMMARY_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    annual_rows = load_annual_rows()
    slot_rows, breakdown_rows = build_slot_rows(annual_rows)
    validation_rows = build_validation_rows(slot_rows, breakdown_rows)

    write_csv(SLOT_OUTPUT_PATH, slot_rows)
    write_csv(BREAKDOWN_OUTPUT_PATH, breakdown_rows)
    write_csv(VALIDATION_OUTPUT_PATH, validation_rows)
    write_summary(slot_rows, validation_rows)

    print(f"Wrote {SLOT_OUTPUT_PATH.name}")
    print(f"Wrote {BREAKDOWN_OUTPUT_PATH.name}")
    print(f"Wrote {VALIDATION_OUTPUT_PATH.name}")
    print(f"Wrote {SUMMARY_OUTPUT_PATH.name}")


if __name__ == "__main__":
    main()
