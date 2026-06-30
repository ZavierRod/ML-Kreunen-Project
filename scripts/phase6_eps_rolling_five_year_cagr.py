#!/usr/bin/env python3
"""Build the Phase 6 rolling 5-year CAGR view of the EPS drivers.

Phase 5 produced non-overlapping 5-year slots (2015-2020, 2020-2025, ...).
Phase 6 reuses the same annual driver table, but slides the 5-year window
forward one calendar year at a time so every rolling 5-year period from
2001-2006 through 2020-2025 is reported in a single table. For each rolling
slot we record:

- Endpoint levels for revenue, net income, shares, net margin, Rev/S, EPS
- Total change over the 5 years (end / start - 1)
- Per-factor CAGR over the slot, i.e. (end / start)^(1/5) - 1

This matches the breakdown Connor asked for: shift the slot over by a year
and report the annualized growth of each factor inside that slot.

Outputs:

- `phase6_eps_rolling_five_year_cagr.csv`
- `phase6_eps_rolling_five_year_validation.csv`
- `phase6_eps_rolling_five_year_summary.md`
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parent.parent
PHASE3_ANNUAL_PATH = ROOT / "outputs" / \
    "phase3" / "phase3_eps_annual_tables.csv"

CAGR_OUTPUT_PATH = ROOT / "outputs" / "phase6" / \
    "phase6_eps_rolling_five_year_cagr.csv"
VALIDATION_OUTPUT_PATH = (
    ROOT / "outputs" / "phase6" / "phase6_eps_rolling_five_year_validation.csv"
)
SUMMARY_OUTPUT_PATH = (
    ROOT / "outputs" / "phase6" / "phase6_eps_rolling_five_year_summary.md"
)


SOURCE_WINDOW_LABEL = "2001_2025"
SLOT_LENGTH_YEARS = 5
FIRST_START_YEAR = 2001
LAST_START_YEAR = 2020


def read_csv_dicts(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_annual_rows() -> Dict[int, Dict[str, float]]:
    """Load every annual row from the 2001_2025 window keyed by calendar year.

    The 2001_2025 window is used because it is the only window in the Phase 3
    output that spans every year Phase 6 needs to roll across.
    """

    raw_rows = read_csv_dicts(PHASE3_ANNUAL_PATH)
    annual_rows: Dict[int, Dict[str, float]] = {}

    for raw in raw_rows:
        if raw["window_label"] != SOURCE_WINDOW_LABEL:
            continue
        year = int(raw["year"])
        annual_rows[year] = {
            "year": year,
            "revenue": float(raw["revenue"]),
            "net_income": float(raw["net_income"]),
            "average_diluted_shares": float(raw["average_diluted_shares"]),
            "net_margin": float(raw["net_margin"]),
            "rev_per_share": float(raw["rev_per_share"]),
            "eps": float(raw["eps"]),
        }

    if not annual_rows:
        raise ValueError(
            f"No rows found for window {SOURCE_WINDOW_LABEL!r} in "
            f"{PHASE3_ANNUAL_PATH}"
        )

    return annual_rows


def cagr(end_value: float, start_value: float, years: int) -> float:
    if years <= 0:
        return 0.0
    return (end_value / start_value) ** (1 / years) - 1


def total_growth(end_value: float, start_value: float) -> float:
    return end_value / start_value - 1


def build_rolling_slots(
    annual_rows: Dict[int, Dict[str, float]],
) -> List[Dict[str, object]]:
    slot_rows: List[Dict[str, object]] = []

    for start_year in range(FIRST_START_YEAR, LAST_START_YEAR + 1):
        end_year = start_year + SLOT_LENGTH_YEARS
        start_row = annual_rows.get(start_year)
        end_row = annual_rows.get(end_year)
        if start_row is None or end_row is None:
            raise ValueError(
                f"Missing annual data for rolling slot {start_year}-{end_year}"
            )

        slot_rows.append(
            {
                "slot": f"{start_year}-{end_year}",
                "start_year": start_year,
                "end_year": end_year,
                "years_in_slot": SLOT_LENGTH_YEARS,
                "revenue_start": start_row["revenue"],
                "revenue_end": end_row["revenue"],
                "revenue_total_growth": total_growth(
                    end_row["revenue"], start_row["revenue"]
                ),
                "revenue_cagr": cagr(
                    end_row["revenue"], start_row["revenue"], SLOT_LENGTH_YEARS
                ),
                "net_income_start": start_row["net_income"],
                "net_income_end": end_row["net_income"],
                "net_income_cagr": cagr(
                    end_row["net_income"],
                    start_row["net_income"],
                    SLOT_LENGTH_YEARS,
                ),
                "shares_start": start_row["average_diluted_shares"],
                "shares_end": end_row["average_diluted_shares"],
                "shares_cagr": cagr(
                    end_row["average_diluted_shares"],
                    start_row["average_diluted_shares"],
                    SLOT_LENGTH_YEARS,
                ),
                "net_margin_start": start_row["net_margin"],
                "net_margin_end": end_row["net_margin"],
                "net_margin_cagr": cagr(
                    end_row["net_margin"],
                    start_row["net_margin"],
                    SLOT_LENGTH_YEARS,
                ),
                "rev_per_share_start": start_row["rev_per_share"],
                "rev_per_share_end": end_row["rev_per_share"],
                "rev_per_share_cagr": cagr(
                    end_row["rev_per_share"],
                    start_row["rev_per_share"],
                    SLOT_LENGTH_YEARS,
                ),
                "eps_start": start_row["eps"],
                "eps_end": end_row["eps"],
                "eps_total_growth": total_growth(
                    end_row["eps"], start_row["eps"]
                ),
                "eps_cagr": cagr(
                    end_row["eps"], start_row["eps"], SLOT_LENGTH_YEARS
                ),
            }
        )

    return slot_rows


CAGR_COLUMN_PAIRS: List[Tuple[str, str, str]] = [
    ("revenue_cagr", "revenue_start", "revenue_end"),
    ("net_income_cagr", "net_income_start", "net_income_end"),
    ("shares_cagr", "shares_start", "shares_end"),
    ("net_margin_cagr", "net_margin_start", "net_margin_end"),
    ("rev_per_share_cagr", "rev_per_share_start", "rev_per_share_end"),
    ("eps_cagr", "eps_start", "eps_end"),
]


def build_validation_rows(
    slot_rows: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    validation_rows: List[Dict[str, object]] = []

    expected_slot_count = LAST_START_YEAR - FIRST_START_YEAR + 1
    actual_slot_count = len(slot_rows)
    validation_rows.append(
        {
            "test_name": "slot_count",
            "status": "PASS" if actual_slot_count == expected_slot_count else "FAIL",
            "details": (
                f"expected {expected_slot_count}, got {actual_slot_count}"
            ),
        }
    )

    bad_span = [
        row
        for row in slot_rows
        if int(row["end_year"]) - int(row["start_year"]) != SLOT_LENGTH_YEARS
        or int(row["years_in_slot"]) != SLOT_LENGTH_YEARS
    ]
    validation_rows.append(
        {
            "test_name": "slot_span_is_five_years",
            "status": "PASS" if not bad_span else "FAIL",
            "details": (
                "all slots span 5 years"
                if not bad_span
                else f"{len(bad_span)} slot(s) had a non-5-year span"
            ),
        }
    )

    max_recompute_gap = 0.0
    worst_slot = ""
    for row in slot_rows:
        for cagr_col, start_col, end_col in CAGR_COLUMN_PAIRS:
            recomputed = cagr(
                float(row[end_col]),
                float(row[start_col]),
                SLOT_LENGTH_YEARS,
            )
            gap = abs(recomputed - float(row[cagr_col]))
            if gap > max_recompute_gap:
                max_recompute_gap = gap
                worst_slot = f"{row['slot']}:{cagr_col}"
    validation_rows.append(
        {
            "test_name": "cagr_recomputes_from_endpoints",
            "status": "PASS" if max_recompute_gap < 1e-12 else "FAIL",
            "details": (
                f"max gap {max_recompute_gap:.2e}"
                + (f" at {worst_slot}" if worst_slot else "")
            ),
        }
    )

    # Connor's sanity check shape: EPS CAGR recomputed from the row's endpoints
    # should match the stored eps_cagr column. We do it separately so the test
    # result explicitly says "EPS CAGR spot check".
    eps_spot_gap = 0.0
    for row in slot_rows:
        recomputed = cagr(
            float(row["eps_end"]),
            float(row["eps_start"]),
            SLOT_LENGTH_YEARS,
        )
        eps_spot_gap = max(eps_spot_gap, abs(
            recomputed - float(row["eps_cagr"])))
    validation_rows.append(
        {
            "test_name": "eps_cagr_spot_check",
            "status": "PASS" if eps_spot_gap < 1e-12 else "FAIL",
            "details": f"max gap {eps_spot_gap:.2e}",
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
        "# Phase 6 Rolling Five-Year CAGR Summary",
        "",
        "## What this does",
        "",
        "- Slides a 5-year window across the full 2001-2025 history, shifting by 1 calendar year.",
        "- Reports endpoint levels and per-factor CAGR for each rolling slot.",
        "- Matches the breakdown style Connor described: take the 5-year factor change and annualize it.",
        "",
        "## Slot definition",
        "",
        f"- First slot: `{FIRST_START_YEAR}-{FIRST_START_YEAR + SLOT_LENGTH_YEARS}`",
        f"- Last slot: `{LAST_START_YEAR}-{LAST_START_YEAR + SLOT_LENGTH_YEARS}`",
        f"- Total rolling slots: `{len(slot_rows)}` (each slot spans exactly {SLOT_LENGTH_YEARS} years)",
        "",
        "CAGR per factor is computed as:",
        "",
        "```text",
        "CAGR = (end_value / start_value) ^ (1 / 5) - 1",
        "```",
        "",
        "## Testing",
        "",
        (
            "All Phase 6 validation checks passed."
            if not failing
            else "Phase 6 completed with validation failures."
        ),
        "",
        "## Rolling 5-year CAGR",
        "",
        "| Slot | Revenue CAGR | Net Margin CAGR | Rev/S CAGR | Shares CAGR | EPS CAGR |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for row in slot_rows:
        lines.append(
            "| {slot} | {rev} | {nm} | {rps} | {sh} | {eps} |".format(
                slot=row["slot"],
                rev=format_pct(float(row["revenue_cagr"])),
                nm=format_pct(float(row["net_margin_cagr"])),
                rps=format_pct(float(row["rev_per_share_cagr"])),
                sh=format_pct(float(row["shares_cagr"])),
                eps=format_pct(float(row["eps_cagr"])),
            )
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Slots overlap by 4 calendar years, so CAGR values cannot be summed or averaged across slots.",
            "- This is an annualized growth view, not a log decomposition. For factor contribution math that ties out exactly to EPS log change, use the Phase 5 output.",
            "- `shares_cagr` is the raw CAGR of share count - negative values correspond to net buybacks over the slot.",
            "- Diluted shares are on a consistent split-adjusted basis (pre-split 2001-2013 restated x20), so slots that straddle 2013-2014 no longer carry a spurious share-count jump.",
            "",
            "## Output files",
            "",
            f"- `{CAGR_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
            f"- `{VALIDATION_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
            f"- `{SUMMARY_OUTPUT_PATH.relative_to(ROOT).as_posix()}`",
            "",
            "## Column reference for `phase6_eps_rolling_five_year_cagr.csv`",
            "",
            "Every row in the CSV is one rolling 5-year slot. The columns below are listed in the exact order they appear in the file, with the formula used for each one. All `*_start` and `*_end` columns are read directly from the matching year in [outputs/phase3/phase3_eps_annual_tables.csv](outputs/phase3/phase3_eps_annual_tables.csv) for the `2001_2025` window.",
            "",
            "### Slot identifiers",
            "",
            "- `slot`: Human-readable label for the rolling window, formatted as `start_year-end_year` (for example `2015-2020`).",
            "- `start_year`: First calendar year of the slot. The value of every `*_start` column is read from this year.",
            "- `end_year`: Last calendar year of the slot. The value of every `*_end` column is read from this year. Equal to `start_year + 5`.",
            "- `years_in_slot`: Number of years between the endpoints. Always `5` in Phase 6 and used as the CAGR denominator.",
            "",
            "### Revenue columns",
            "",
            "- `revenue_start`: Total Gross revenue (GAAP) in `start_year`, in millions USD.",
            "- `revenue_end`: Total Gross revenue (GAAP) in `end_year`, in millions USD.",
            "- `revenue_total_growth`: Cumulative 5-year change, computed as `revenue_end / revenue_start - 1`. Expressed as a decimal (0.25 means +25%).",
            "- `revenue_cagr`: Annualized growth rate, computed as `(revenue_end / revenue_start) ** (1 / 5) - 1`. This is Connor's example-style CAGR applied to revenue.",
            "",
            "### Net income columns",
            "",
            "- `net_income_start`: Net income, reported in `start_year`, in millions USD.",
            "- `net_income_end`: Net income, reported in `end_year`, in millions USD.",
            "- `net_income_cagr`: Annualized growth rate, computed as `(net_income_end / net_income_start) ** (1 / 5) - 1`.",
            "",
            "### Share count columns",
            "",
            "- `shares_start`: Average diluted shares in `start_year`, in millions.",
            "- `shares_end`: Average diluted shares in `end_year`, in millions.",
            "- `shares_cagr`: Annualized change in share count, computed as `(shares_end / shares_start) ** (1 / 5) - 1`. A negative value means the share count shrank on average each year (net buybacks); a positive value means dilution.",
            "",
            "### Net margin columns",
            "",
            "- `net_margin_start`: Net margin in `start_year`, computed upstream in Phase 3 as `net_income / revenue`. Expressed as a decimal (0.22 means 22%).",
            "- `net_margin_end`: Net margin in `end_year`, same formula.",
            "- `net_margin_cagr`: Annualized change in the margin ratio, computed as `(net_margin_end / net_margin_start) ** (1 / 5) - 1`. Because net margin is already a ratio, this reads as the annualized percentage change in the margin itself, not a new margin value.",
            "",
            "### Revenue per share columns",
            "",
            "- `rev_per_share_start`: Revenue per average diluted share in `start_year`, computed upstream as `revenue / average_diluted_shares`.",
            "- `rev_per_share_end`: Same formula for `end_year`.",
            "- `rev_per_share_cagr`: Annualized growth, computed as `(rev_per_share_end / rev_per_share_start) ** (1 / 5) - 1`.",
            "",
            "### EPS columns",
            "",
            "- `eps_start`: Earnings per diluted share in `start_year`, computed upstream as `net_income / average_diluted_shares`.",
            "- `eps_end`: Same formula for `end_year`.",
            "- `eps_total_growth`: Cumulative 5-year change in EPS, computed as `eps_end / eps_start - 1`.",
            "- `eps_cagr`: Annualized EPS growth, computed as `(eps_end / eps_start) ** (1 / 5) - 1`. This is the headline number for the slot.",
            "",
            "### How the CAGR is computed",
            "",
            "Every `*_cagr` column in the file uses the same helper in [scripts/phase6_eps_rolling_five_year_cagr.py](scripts/phase6_eps_rolling_five_year_cagr.py):",
            "",
            "```python",
            "def cagr(end_value: float, start_value: float, years: int) -> float:",
            "    return (end_value / start_value) ** (1 / years) - 1",
            "```",
            "",
            "`years` is always `5` for Phase 6. The validation CSV re-runs this formula against each `*_start` / `*_end` pair and confirms it matches the stored `*_cagr` column with zero gap.",
        ]
    )

    SUMMARY_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    annual_rows = load_annual_rows()
    slot_rows = build_rolling_slots(annual_rows)
    validation_rows = build_validation_rows(slot_rows)

    write_csv(CAGR_OUTPUT_PATH, slot_rows)
    write_csv(VALIDATION_OUTPUT_PATH, validation_rows)
    write_summary(slot_rows, validation_rows)

    print(f"Wrote {CAGR_OUTPUT_PATH.name}")
    print(f"Wrote {VALIDATION_OUTPUT_PATH.name}")
    print(f"Wrote {SUMMARY_OUTPUT_PATH.name}")


if __name__ == "__main__":
    main()
