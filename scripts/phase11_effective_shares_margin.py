#!/usr/bin/env python3
"""Effective shares and net margin factors for the GOOG ML project (Phase 11).

Phase 11 builds two Derek-requested effective-change metrics on top of the
Phase 9 factor levels. No new data pull.

Definitions (all deltas are SIMPLE year-over-year percent change,
`level_t / level_t-1 - 1`, matching Phase 9):

1. eff.Shares (effective change in shares):
       base = (Shares_t-1 / Shares_t - 1)
       eff.Shares = base + base * dRevenue
                  = base * (1 + dRevenue)
   where dRevenue is the current year's simple percent change in total Revenue.

2. eff.NetMargin (effective change in net margin):
       base = (Net Margin_t / Net Margin_t-1 - 1)
       eff.NetMargin = base + base * dRevPerShare
                     = base * (1 + dRevPerShare)
   where dRevPerShare is the current year's simple percent change in
   Revenue per share (Revenue / diluted Shares).

Inputs:

- `outputs/phase9/phase9_factor_levels.csv` (Revenue, Net Margin, Shares)

Outputs (in outputs/phase11/):

- `phase11_factor_levels.csv`
- `phase11_effective_panel.csv`
- `phase11_effective_summary_full_2001_2025.csv`
- `phase11_effective_summary_recent5_2020_2025.csv`
- `phase11_combined_ranking_full_2001_2025.csv`
- `phase11_combined_ranking_recent5_2020_2025.csv`
- `phase11_validation_results.csv`
- `phase11_summary.md`
- `presentation_tables/table17_effective_summary_full_2001-2025.csv`
- `presentation_tables/table18_effective_summary_recent5_2020-2025.csv`
- `presentation_tables/table19_combined_ranking_full_2001-2025.csv`
- `presentation_tables/table20_combined_ranking_recent5_2020-2025.csv`
"""

from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
LEVELS_INPUT = ROOT / "outputs" / "phase9" / "phase9_factor_levels.csv"

OUTPUT_DIR = ROOT / "outputs" / "phase11"
PRESENTATION_DIR = OUTPUT_DIR / "presentation_tables"

LEVELS_PATH = OUTPUT_DIR / "phase11_factor_levels.csv"
PANEL_PATH = OUTPUT_DIR / "phase11_effective_panel.csv"
FULL_SUMMARY_PATH = OUTPUT_DIR / "phase11_effective_summary_full_2001_2025.csv"
RECENT_SUMMARY_PATH = OUTPUT_DIR / "phase11_effective_summary_recent5_2020_2025.csv"
COMBINED_FULL_PATH = OUTPUT_DIR / "phase11_combined_ranking_full_2001_2025.csv"
COMBINED_RECENT_PATH = (
    OUTPUT_DIR / "phase11_combined_ranking_recent5_2020_2025.csv"
)
VALIDATION_PATH = OUTPUT_DIR / "phase11_validation_results.csv"
SUMMARY_PATH = OUTPUT_DIR / "phase11_summary.md"
PRES_FULL_PATH = (
    PRESENTATION_DIR / "table17_effective_summary_full_2001-2025.csv"
)
PRES_RECENT_PATH = (
    PRESENTATION_DIR / "table18_effective_summary_recent5_2020-2025.csv"
)
PRES_COMBINED_FULL_PATH = (
    PRESENTATION_DIR / "table19_combined_ranking_full_2001-2025.csv"
)
PRES_COMBINED_RECENT_PATH = (
    PRESENTATION_DIR / "table20_combined_ranking_recent5_2020-2025.csv"
)

START_YEAR = 2001
END_YEAR = 2025
RECENT_START_YEAR = 2020

METRICS = ["eff_shares_change", "eff_net_margin_change"]

PHASE9_FACTORS = [
    "Revenue",
    "Net Margin",
    "EPS",
    "FCF",
    "NetCash",
    "Shares",
    "Price",
]


def read_csv_dicts(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def to_optional_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = value.strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def load_factor_levels() -> Dict[int, Dict[str, Optional[float]]]:
    if not LEVELS_INPUT.exists():
        raise FileNotFoundError(
            f"Missing {LEVELS_INPUT.relative_to(ROOT)}; run Phase 9 first."
        )
    levels: Dict[int, Dict[str, Optional[float]]] = {}
    for row in read_csv_dicts(LEVELS_INPUT):
        year = int(row["year"])
        levels[year] = {
            factor: to_optional_float(row.get(factor)) for factor in PHASE9_FACTORS
        }
    return levels


def rev_per_share(level: Dict[str, Optional[float]]) -> Optional[float]:
    revenue = level["Revenue"]
    shares = level["Shares"]
    if revenue is None or shares is None or shares == 0:
        return None
    return revenue / shares


def simple_pct_change(prev: Optional[float], cur: Optional[float]) -> Optional[float]:
    if prev is None or cur is None or prev == 0:
        return None
    return cur / prev - 1


def effective_change(
    base_change: Optional[float], driver_change: Optional[float]
) -> Optional[float]:
    if base_change is None or driver_change is None:
        return None
    return base_change * (1 + driver_change)


def shares_base_change(prev_shares: Optional[float], cur_shares: Optional[float]) -> Optional[float]:
    """Derek formula: (Previous Year # of shares / Current Year # of shares) - 1."""
    if prev_shares is None or cur_shares is None or cur_shares == 0:
        return None
    return prev_shares / cur_shares - 1


def build_levels_rows(
    levels: Dict[int, Dict[str, Optional[float]]],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for year in sorted(levels):
        if year < START_YEAR or year > END_YEAR:
            continue
        level = levels[year]
        rows.append(
            {
                "year": year,
                "Revenue": level["Revenue"],
                "Rev_per_share": rev_per_share(level),
                "Net Margin": level["Net Margin"],
                "Shares": level["Shares"],
            }
        )
    return rows


def build_panel_rows(
    levels: Dict[int, Dict[str, Optional[float]]],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    years = [y for y in sorted(levels) if START_YEAR <= y <= END_YEAR]

    for index in range(1, len(years)):
        prev_year, cur_year = years[index - 1], years[index]
        prev, cur = levels[prev_year], levels[cur_year]

        revenue_chg = simple_pct_change(prev["Revenue"], cur["Revenue"])
        margin_chg = simple_pct_change(prev["Net Margin"], cur["Net Margin"])
        shares_chg = simple_pct_change(prev["Shares"], cur["Shares"])
        rev_per_share_chg = simple_pct_change(
            rev_per_share(prev), rev_per_share(cur)
        )

        shares_base = shares_base_change(prev["Shares"], cur["Shares"])
        eff_shares = effective_change(shares_base, revenue_chg)
        eff_margin = effective_change(margin_chg, rev_per_share_chg)

        rows.append(
            {
                "from_year": prev_year,
                "to_year": cur_year,
                "period": f"{prev_year}-{cur_year}",
                "Revenue_pct_change": revenue_chg,
                "Shares_pct_change": shares_chg,
                "shares_base_change": shares_base,
                "eff_shares_change": eff_shares,
                "Net_Margin_pct_change": margin_chg,
                "Rev_per_share_pct_change": rev_per_share_chg,
                "eff_net_margin_change": eff_margin,
            }
        )
    return rows


def summarize(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    summaries: List[Dict[str, object]] = []
    for metric in METRICS:
        values = [float(row[metric]) for row in rows if row[metric] is not None]
        if not values:
            summaries.append(
                {
                    "metric": metric,
                    "periods": 0,
                    "mean_abs": None,
                    "mean": None,
                    "positive_periods": 0,
                    "negative_periods": 0,
                }
            )
            continue
        summaries.append(
            {
                "metric": metric,
                "periods": len(values),
                "mean_abs": round(statistics.fmean(abs(v) for v in values), 6),
                "mean": round(statistics.fmean(values), 6),
                "positive_periods": sum(1 for v in values if v > 0),
                "negative_periods": sum(1 for v in values if v < 0),
            }
        )

    summaries.sort(
        key=lambda row: row["mean_abs"] if row["mean_abs"] is not None else -1.0,
        reverse=True,
    )
    for index, row in enumerate(summaries, start=1):
        row["overall_rank"] = index

    ordered = [
        "overall_rank",
        "metric",
        "mean_abs",
        "mean",
        "positive_periods",
        "negative_periods",
        "periods",
    ]
    return [{key: row[key] for key in ordered} for row in summaries]


def recent_rows(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    return [row for row in rows if int(row["from_year"]) >= RECENT_START_YEAR]


def factor_pct_series(
    factor_levels: Dict[int, Dict[str, Optional[float]]],
    factor: str,
) -> List[Dict[str, object]]:
    years = sorted(factor_levels)
    series: List[Dict[str, object]] = []
    for index in range(1, len(years)):
        prev_year, cur_year = years[index - 1], years[index]
        series.append(
            {
                "from_year": prev_year,
                "to_year": cur_year,
                "pct": simple_pct_change(
                    factor_levels[prev_year][factor],
                    factor_levels[cur_year][factor],
                ),
            }
        )
    return series


def panel_metric_series(
    panel_rows: List[Dict[str, object]], key: str
) -> List[Dict[str, object]]:
    return [
        {"from_year": row["from_year"], "to_year": row["to_year"], "pct": row[key]}
        for row in panel_rows
    ]


def window_stats(
    series: List[Dict[str, object]], start: int, end: int
) -> Optional[Dict[str, object]]:
    values = [
        float(row["pct"])
        for row in series
        if row["pct"] is not None
        and int(row["from_year"]) >= start
        and int(row["to_year"]) <= end
    ]
    if not values:
        return None
    return {
        "mean_abs": round(statistics.fmean(abs(v) for v in values), 6),
        "mean": round(statistics.fmean(values), 6),
        "positive_periods": sum(1 for v in values if v > 0),
        "negative_periods": sum(1 for v in values if v < 0),
        "periods": len(values),
    }


def build_combined_ranking(
    factor_levels: Dict[int, Dict[str, Optional[float]]],
    panel_rows: List[Dict[str, object]],
    start: int,
    end: int,
) -> List[Dict[str, object]]:
    entries: List[tuple] = [
        ("factor", factor, factor_pct_series(factor_levels, factor))
        for factor in PHASE9_FACTORS
    ]
    entries.append(
        (
            "derived-effective",
            "eff.Shares",
            panel_metric_series(panel_rows, "eff_shares_change"),
        )
    )
    entries.append(
        (
            "derived-effective",
            "eff.NetMargin",
            panel_metric_series(panel_rows, "eff_net_margin_change"),
        )
    )

    rows: List[Dict[str, object]] = []
    for metric_type, name, series in entries:
        stats = window_stats(series, start, end)
        if stats is None:
            continue
        rows.append({"metric": name, "type": metric_type, **stats})

    rows.sort(key=lambda row: row["mean_abs"], reverse=True)
    for index, row in enumerate(rows, start=1):
        row["overall_rank"] = index

    ordered = [
        "overall_rank",
        "metric",
        "type",
        "mean_abs",
        "mean",
        "positive_periods",
        "negative_periods",
        "periods",
    ]
    return [{key: row[key] for key in ordered} for row in rows]


def build_validation_rows(
    factor_levels: Dict[int, Dict[str, Optional[float]]],
    panel_rows: List[Dict[str, object]],
    combined_full: List[Dict[str, object]],
    combined_recent: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    validation: List[Dict[str, object]] = []

    loaded_years = sum(
        1 for year in factor_levels if START_YEAR <= year <= END_YEAR
    )
    validation.append(
        {
            "test_name": "levels_loaded",
            "status": "PASS"
            if loaded_years == (END_YEAR - START_YEAR + 1)
            else "FAIL",
            "details": f"loaded {loaded_years} years in {START_YEAR}-{END_YEAR}",
        }
    )

    expected_periods = END_YEAR - START_YEAR
    validation.append(
        {
            "test_name": "effective_period_count",
            "status": "PASS" if len(panel_rows) == expected_periods else "FAIL",
            "details": f"expected {expected_periods}, got {len(panel_rows)}",
        }
    )

    first = min(panel_rows, key=lambda row: int(row["from_year"]))
    validation.append(
        {
            "test_name": "first_period_is_2001_2002",
            "status": "PASS" if int(first["from_year"]) == START_YEAR else "FAIL",
            "details": f"first period {first['period']}",
        }
    )

    recent = recent_rows(panel_rows)
    validation.append(
        {
            "test_name": "recent5_period_count",
            "status": "PASS" if len(recent) == 5 else "FAIL",
            "details": f"expected 5, got {len(recent)}",
        }
    )

    eff_shares_gap = 0.0
    eff_margin_gap = 0.0
    for row in panel_rows:
        shares_base = row["shares_base_change"]
        revenue_chg = row["Revenue_pct_change"]
        eff_shares = row["eff_shares_change"]
        if shares_base is not None and revenue_chg is not None and eff_shares is not None:
            eff_shares_gap = max(
                eff_shares_gap,
                abs(eff_shares - shares_base * (1 + revenue_chg)),
            )

        margin_chg = row["Net_Margin_pct_change"]
        rev_ps_chg = row["Rev_per_share_pct_change"]
        eff_margin = row["eff_net_margin_change"]
        if margin_chg is not None and rev_ps_chg is not None and eff_margin is not None:
            eff_margin_gap = max(
                eff_margin_gap,
                abs(eff_margin - margin_chg * (1 + rev_ps_chg)),
            )

    validation.append(
        {
            "test_name": "eff_shares_identity",
            "status": "PASS" if eff_shares_gap < 1e-9 else "FAIL",
            "details": (
                "max |eff.Shares - base*(1+dRevenue)| = "
                f"{eff_shares_gap:.2e}"
            ),
        }
    )
    validation.append(
        {
            "test_name": "eff_net_margin_identity",
            "status": "PASS" if eff_margin_gap < 1e-9 else "FAIL",
            "details": (
                "max |eff.NetMargin - base*(1+dRevPerShare)| = "
                f"{eff_margin_gap:.2e}"
            ),
        }
    )

    all_finite = all(
        row[metric] is None or math.isfinite(float(row[metric]))
        for row in panel_rows
        for metric in (
            "Revenue_pct_change",
            "Shares_pct_change",
            "shares_base_change",
            "eff_shares_change",
            "Net_Margin_pct_change",
            "Rev_per_share_pct_change",
            "eff_net_margin_change",
        )
    )
    validation.append(
        {
            "test_name": "all_values_finite",
            "status": "PASS" if all_finite else "FAIL",
            "details": "checked every populated metric in every period",
        }
    )

    expected_rows = len(PHASE9_FACTORS) + 2
    for label, table in (
        ("combined_full", combined_full),
        ("combined_recent", combined_recent),
    ):
        validation.append(
            {
                "test_name": f"{label}_row_count",
                "status": "PASS" if len(table) == expected_rows else "FAIL",
                "details": f"expected {expected_rows}, got {len(table)}",
            }
        )

    for label, table, expected_periods, window_start, window_end in (
        ("combined_full", combined_full, END_YEAR - START_YEAR, START_YEAR, END_YEAR),
        (
            "combined_recent",
            combined_recent,
            END_YEAR - RECENT_START_YEAR,
            RECENT_START_YEAR,
            END_YEAR,
        ),
    ):
        period_counts = {int(row["periods"]) for row in table}
        price_rows = [row for row in table if row["metric"] == "Price"]
        non_price_rows = [row for row in table if row["metric"] != "Price"]
        non_price_periods = {int(row["periods"]) for row in non_price_rows}
        validation.append(
            {
                "test_name": f"{label}_non_price_periods_aligned",
                "status": "PASS"
                if non_price_periods == {expected_periods}
                else "FAIL",
                "details": (
                    f"expected all non-Price rows = {expected_periods} periods, "
                    f"got {sorted(non_price_periods)}"
                ),
            }
        )
        if price_rows:
            price_start = max(2004, window_start)
            expected_price_periods = window_end - price_start
            price_periods = {int(row["periods"]) for row in price_rows}
            validation.append(
                {
                    "test_name": f"{label}_price_periods",
                    "status": "PASS"
                    if price_periods == {expected_price_periods}
                    else "FAIL",
                    "details": (
                        f"expected Price = {expected_price_periods} periods, "
                        f"got {sorted(price_periods)}"
                    ),
                }
            )

    shares_from_factors = window_stats(
        factor_pct_series(factor_levels, "Shares"), START_YEAR, END_YEAR
    )
    shares_from_panel = window_stats(
        panel_metric_series(panel_rows, "Shares_pct_change"), START_YEAR, END_YEAR
    )
    shares_gap = abs(
        float(shares_from_factors["mean_abs"]) - float(shares_from_panel["mean_abs"])
    )
    validation.append(
        {
            "test_name": "shares_series_consistent",
            "status": "PASS" if shares_gap < 1e-9 else "FAIL",
            "details": (
                "Shares mean_abs from Phase 9 levels vs panel "
                f"differ by {shares_gap:.2e}"
            ),
        }
    )

    return validation


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows were generated for {path.name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: ("" if value is None else value)
                    for key, value in row.items()
                }
            )


def md_table(headers: List[str], rows: List[List[str]]) -> List[str]:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def pct(value: object) -> str:
    if value is None or value == "":
        return "n/a"
    return f"{float(value) * 100:.1f}%"


def metric_label(metric: str) -> str:
    return {
        "eff_shares_change": "eff.Shares",
        "eff_net_margin_change": "eff.NetMargin",
    }.get(metric, metric)


def write_summary(
    full_summary: List[Dict[str, object]],
    recent_summary: List[Dict[str, object]],
    combined_full: List[Dict[str, object]],
    combined_recent: List[Dict[str, object]],
    validation_rows: List[Dict[str, object]],
) -> None:
    failing = [row for row in validation_rows if row["status"] != "PASS"]

    def summary_table(rows: List[Dict[str, object]]) -> List[str]:
        return md_table(
            ["Rank", "Metric", "Mean |%|", "Mean %", "Up", "Down"],
            [
                [
                    str(row["overall_rank"]),
                    metric_label(str(row["metric"])),
                    pct(row["mean_abs"]),
                    pct(row["mean"]),
                    str(row["positive_periods"]),
                    str(row["negative_periods"]),
                ]
                for row in rows
            ],
        )

    def combined_table(rows: List[Dict[str, object]]) -> List[str]:
        return md_table(
            ["Rank", "Metric", "Type", "Mean |%|", "Mean %", "Up", "Down"],
            [
                [
                    str(row["overall_rank"]),
                    str(row["metric"]),
                    str(row["type"]),
                    pct(row["mean_abs"]),
                    pct(row["mean"]),
                    str(row["positive_periods"]),
                    str(row["negative_periods"]),
                ]
                for row in rows
            ],
        )

    lines: List[str] = [
        "# Phase 11 Effective Shares & Net Margin Summary",
        "",
        "## Testing",
        "",
        (
            "All Phase 11 validation checks passed."
            if not failing
            else "Phase 11 completed with validation FAILURES: "
            + ", ".join(row["test_name"] for row in failing)
        ),
        "",
        "Validation file: `outputs/phase11/phase11_validation_results.csv`",
        "",
        "## Method",
        "",
        "- Builds on Phase 9 levels (`outputs/phase9/phase9_factor_levels.csv`); no new data pull.",
        "- All deltas are SIMPLE year-over-year percent change, `level_t / level_t-1 - 1` (same as Phase 9).",
        "- `eff.Shares = (Shares_t-1 / Shares_t - 1) * (1 + dRevenue)`, where dRevenue is the current year's simple percent change in total Revenue.",
        "- `eff.NetMargin = (Net Margin_t / Net Margin_t-1 - 1) * (1 + dRevPerShare)`, where dRevPerShare is the current year's simple percent change in Revenue per share.",
        "- Revenue per share = total Revenue / diluted Shares.",
        f"- Full history covers {START_YEAR}-{END_YEAR} ({END_YEAR - START_YEAR} year-over-year periods).",
        "- Reported as a standalone effective-change panel, NOT folded into the Phase 9 seven-factor weights.",
        "",
        f"## Summary - Full History ({START_YEAR}-{END_YEAR})",
        "",
    ]
    lines.extend(summary_table(full_summary))
    lines.extend(
        [
            "",
            f"## Summary - Recent 5 Years ({RECENT_START_YEAR}-{END_YEAR})",
            "",
        ]
    )
    lines.extend(summary_table(recent_summary))
    lines.extend(
        [
            "",
            "## Combined Ranking with Phase 9 Factors",
            "",
            "The Phase 9 factors and the new effective metrics ranked together by average "
            "size of move (`mean_abs`). This is a comparison of movers only: there is "
            "deliberately NO weight column, because eff.Shares and eff.NetMargin are "
            "derived from Shares, Revenue, Net Margin, and Rev/Share, so folding them "
            "into the Phase 9 share-of-movement weighting would double-count. "
            "`type` flags each row as `factor` or `derived-effective`.",
            "",
            f"### Combined - Full History ({START_YEAR}-{END_YEAR})",
            "",
        ]
    )
    lines.extend(combined_table(combined_full))
    lines.extend(
        [
            "",
            f"### Combined - Recent 5 Years ({RECENT_START_YEAR}-{END_YEAR})",
            "",
        ]
    )
    lines.extend(combined_table(combined_recent))
    lines.extend(
        [
            "",
            "## Output Files",
            "",
            "- `outputs/phase11/phase11_factor_levels.csv`",
            "- `outputs/phase11/phase11_effective_panel.csv`",
            "- `outputs/phase11/phase11_effective_summary_full_2001_2025.csv`",
            "- `outputs/phase11/phase11_effective_summary_recent5_2020_2025.csv`",
            "- `outputs/phase11/phase11_combined_ranking_full_2001_2025.csv`",
            "- `outputs/phase11/phase11_combined_ranking_recent5_2020_2025.csv`",
            "- `outputs/phase11/phase11_validation_results.csv`",
            "- `outputs/phase11/presentation_tables/table17_effective_summary_full_2001-2025.csv`",
            "- `outputs/phase11/presentation_tables/table18_effective_summary_recent5_2020-2025.csv`",
            "- `outputs/phase11/presentation_tables/table19_combined_ranking_full_2001-2025.csv`",
            "- `outputs/phase11/presentation_tables/table20_combined_ranking_recent5_2020-2025.csv`",
        ]
    )

    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def presentation_summary(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    return [
        {
            **row,
            "metric": metric_label(str(row["metric"])),
        }
        for row in rows
    ]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PRESENTATION_DIR.mkdir(parents=True, exist_ok=True)

    factor_levels = load_factor_levels()
    levels_rows = build_levels_rows(factor_levels)
    panel_rows = build_panel_rows(factor_levels)
    full_summary = summarize(panel_rows)
    recent_summary = summarize(recent_rows(panel_rows))
    combined_full = build_combined_ranking(
        factor_levels, panel_rows, START_YEAR, END_YEAR
    )
    combined_recent = build_combined_ranking(
        factor_levels, panel_rows, RECENT_START_YEAR, END_YEAR
    )
    validation_rows = build_validation_rows(
        factor_levels, panel_rows, combined_full, combined_recent
    )

    write_csv(LEVELS_PATH, levels_rows)
    write_csv(PANEL_PATH, panel_rows)
    write_csv(FULL_SUMMARY_PATH, presentation_summary(full_summary))
    write_csv(RECENT_SUMMARY_PATH, presentation_summary(recent_summary))
    write_csv(COMBINED_FULL_PATH, combined_full)
    write_csv(COMBINED_RECENT_PATH, combined_recent)
    write_csv(VALIDATION_PATH, validation_rows)
    write_csv(PRES_FULL_PATH, presentation_summary(full_summary))
    write_csv(PRES_RECENT_PATH, presentation_summary(recent_summary))
    write_csv(PRES_COMBINED_FULL_PATH, combined_full)
    write_csv(PRES_COMBINED_RECENT_PATH, combined_recent)
    write_summary(
        full_summary, recent_summary, combined_full, combined_recent, validation_rows
    )

    for path in (
        LEVELS_PATH,
        PANEL_PATH,
        FULL_SUMMARY_PATH,
        RECENT_SUMMARY_PATH,
        COMBINED_FULL_PATH,
        COMBINED_RECENT_PATH,
        VALIDATION_PATH,
        PRES_FULL_PATH,
        PRES_RECENT_PATH,
        PRES_COMBINED_FULL_PATH,
        PRES_COMBINED_RECENT_PATH,
        SUMMARY_PATH,
    ):
        print(f"Wrote {path.relative_to(ROOT)}")

    failing = [row for row in validation_rows if row["status"] != "PASS"]
    if failing:
        print("VALIDATION FAILURES:")
        for row in failing:
            print(f"  {row['test_name']}: {row['details']}")
    else:
        print("All validation checks PASSED.")


if __name__ == "__main__":
    main()
