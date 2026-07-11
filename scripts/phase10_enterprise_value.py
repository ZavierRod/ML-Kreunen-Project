#!/usr/bin/env python3
"""Enterprise Value chain for the GOOG ML project (Phase 10).

Phase 10 builds a standalone Enterprise Value (EV) panel on top of the
Phase 9 factor levels. It reuses the per-share Price, total NetCash, diluted
Shares, and Free Cash Flow already produced in Phase 9 -- no new data pull.

Definitions (all deltas are SIMPLE year-over-year percent change,
`level_t / level_t-1 - 1`, matching Phase 9):

1. EV (a per-share LEVEL) = Price - NetCash/share, where
   NetCash/share = NetCash_total / diluted Shares. Then take dEV.
2. eff.dCash (a delta) = dEV - dPrice.
3. C-Return (a delta) = dFCF - eff.dCash.

FCF uses the same total Free Cash Flow simple percent change as the Phase 9
FCF factor (confirmed: simple percent change is fine for the C-Return step).

EV depends on Price, so the panel starts with the 2004-2005 period (Price
begins 2004 when Google went public).

Inputs:

- `outputs/phase9/phase9_factor_levels.csv` (Price, NetCash, Shares, FCF)

Outputs (in outputs/phase10/):

- `phase10_ev_levels.csv`
- `phase10_ev_c_return_panel.csv`
- `phase10_ev_c_return_summary_full_2004_2025.csv`
- `phase10_ev_c_return_summary_recent5_2020_2025.csv`
- `phase10_validation_results.csv`
- `phase10_summary.md`
- `presentation_tables/table13_ev_c_return_summary_full_2004-2025.csv`
- `presentation_tables/table14_ev_c_return_summary_recent5_2020-2025.csv`
"""

from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
LEVELS_INPUT = ROOT / "outputs" / "phase9" / "phase9_factor_levels.csv"

OUTPUT_DIR = ROOT / "outputs" / "phase10"
PRESENTATION_DIR = OUTPUT_DIR / "presentation_tables"

EV_LEVELS_PATH = OUTPUT_DIR / "phase10_ev_levels.csv"
PANEL_PATH = OUTPUT_DIR / "phase10_ev_c_return_panel.csv"
FULL_SUMMARY_PATH = OUTPUT_DIR / "phase10_ev_c_return_summary_full_2004_2025.csv"
RECENT_SUMMARY_PATH = OUTPUT_DIR / "phase10_ev_c_return_summary_recent5_2020_2025.csv"
VALIDATION_PATH = OUTPUT_DIR / "phase10_validation_results.csv"
SUMMARY_PATH = OUTPUT_DIR / "phase10_summary.md"
PRES_FULL_PATH = PRESENTATION_DIR / "table13_ev_c_return_summary_full_2004-2025.csv"
PRES_RECENT_PATH = (
    PRESENTATION_DIR / "table14_ev_c_return_summary_recent5_2020-2025.csv"
)

# Combined ranking (Phase 9 factors + the new EV metrics), ranked by mean_abs on
# a shared window. No weight column: the Phase 9 share-of-movement weighting is
# left untouched because EV/eff.dCash/C-Return are derived from existing factors.
COMBINED_FULL_PATH = OUTPUT_DIR / "phase10_combined_ranking_full_2004_2025.csv"
COMBINED_RECENT_PATH = (
    OUTPUT_DIR / "phase10_combined_ranking_recent5_2020_2025.csv"
)
PRES_COMBINED_FULL_PATH = (
    PRESENTATION_DIR / "table15_combined_ranking_full_2004-2025.csv"
)
PRES_COMBINED_RECENT_PATH = (
    PRESENTATION_DIR / "table16_combined_ranking_recent5_2020-2025.csv"
)

# EV history starts once Price exists (GOOG IPO in 2004).
EV_START_YEAR = 2004
END_YEAR = 2025
RECENT_START_YEAR = 2020

# Metrics carried through the panel and summarized (ranked by mean_abs).
METRICS = ["EV_pct_change", "eff_delta_cash", "FCF_pct_change", "c_return"]

# The seven Phase 9 factors, read as levels straight from the Phase 9 levels file.
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


def load_levels() -> Dict[int, Dict[str, Optional[float]]]:
    if not LEVELS_INPUT.exists():
        raise FileNotFoundError(
            f"Missing {LEVELS_INPUT.relative_to(ROOT)}; run Phase 9 first."
        )
    levels: Dict[int, Dict[str, Optional[float]]] = {}
    for row in read_csv_dicts(LEVELS_INPUT):
        year = int(row["year"])
        levels[year] = {
            "Price": to_optional_float(row.get("Price")),
            "NetCash": to_optional_float(row.get("NetCash")),
            "Shares": to_optional_float(row.get("Shares")),
            "FCF": to_optional_float(row.get("FCF")),
        }
    return levels


def load_factor_levels() -> Dict[int, Dict[str, Optional[float]]]:
    """Load the seven Phase 9 factor levels (as-is columns) keyed by year."""
    levels: Dict[int, Dict[str, Optional[float]]] = {}
    for row in read_csv_dicts(LEVELS_INPUT):
        year = int(row["year"])
        levels[year] = {
            factor: to_optional_float(row.get(factor)) for factor in PHASE9_FACTORS
        }
    return levels


def net_cash_per_share(level: Dict[str, Optional[float]]) -> Optional[float]:
    net_cash = level["NetCash"]
    shares = level["Shares"]
    if net_cash is None or shares is None or shares == 0:
        return None
    return net_cash / shares


def enterprise_value_per_share(level: Dict[str, Optional[float]]) -> Optional[float]:
    price = level["Price"]
    ncash_per_share = net_cash_per_share(level)
    if price is None or ncash_per_share is None:
        return None
    return price - ncash_per_share


def simple_pct_change(prev: Optional[float], cur: Optional[float]) -> Optional[float]:
    if prev is None or cur is None or prev == 0:
        return None
    return cur / prev - 1


def build_ev_levels_rows(
    levels: Dict[int, Dict[str, Optional[float]]],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for year in sorted(levels):
        if year < EV_START_YEAR:
            continue
        level = levels[year]
        rows.append(
            {
                "year": year,
                "Price": level["Price"],
                "NetCash_total": level["NetCash"],
                "Shares": level["Shares"],
                "NetCash_per_share": net_cash_per_share(level),
                "EV_per_share": enterprise_value_per_share(level),
                "FCF_total": level["FCF"],
            }
        )
    return rows


def subtract(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    return a - b


def build_panel_rows(
    levels: Dict[int, Dict[str, Optional[float]]],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    years = [y for y in sorted(levels) if y >= EV_START_YEAR and y <= END_YEAR]
    for index in range(1, len(years)):
        prev_year, cur_year = years[index - 1], years[index]
        prev, cur = levels[prev_year], levels[cur_year]

        price_chg = simple_pct_change(prev["Price"], cur["Price"])
        ev_chg = simple_pct_change(
            enterprise_value_per_share(prev),
            enterprise_value_per_share(cur),
        )
        fcf_chg = simple_pct_change(prev["FCF"], cur["FCF"])

        eff_delta_cash = subtract(ev_chg, price_chg)
        c_return = subtract(fcf_chg, eff_delta_cash)

        rows.append(
            {
                "from_year": prev_year,
                "to_year": cur_year,
                "period": f"{prev_year}-{cur_year}",
                "Price_pct_change": price_chg,
                "EV_pct_change": ev_chg,
                "eff_delta_cash": eff_delta_cash,
                "FCF_pct_change": fcf_chg,
                "c_return": c_return,
            }
        )
    return rows


def summarize(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    summaries: List[Dict[str, object]] = []
    for metric in METRICS:
        values = [
            float(row[metric]) for row in rows if row[metric] is not None
        ]
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
                "mean_abs": round(
                    statistics.fmean(abs(v) for v in values), 6
                ),
                "mean": round(statistics.fmean(values), 6),
                "positive_periods": sum(1 for v in values if v > 0),
                "negative_periods": sum(1 for v in values if v < 0),
            }
        )

    summaries.sort(
        key=lambda row: (
            row["mean_abs"] if row["mean_abs"] is not None else -1.0
        ),
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
    """Simple YoY percent change for one Phase 9 factor over all adjacent years."""
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
    panel_rows: List[Dict[str, object]],
    key: str,
) -> List[Dict[str, object]]:
    """Pull one already-computed metric out of the EV panel as a period series."""
    return [
        {"from_year": row["from_year"], "to_year": row["to_year"], "pct": row[key]}
        for row in panel_rows
    ]


def window_stats(
    series: List[Dict[str, object]], start: int, end: int
) -> Optional[Dict[str, object]]:
    """Mean, mean-abs, and up/down counts for a period series within a window."""
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
    """Rank Phase 9 factors + the new EV metrics together by mean_abs on a shared
    window. FCF appears once (as the Phase 9 factor); the derived EV metrics are
    labeled so nobody reads them as independent factors. No weight column."""
    entries: List[tuple] = [
        ("factor", factor, factor_pct_series(factor_levels, factor))
        for factor in PHASE9_FACTORS
    ]
    entries.append(
        ("derived-level", "EV", panel_metric_series(panel_rows, "EV_pct_change"))
    )
    entries.append(
        (
            "derived-delta",
            "eff.dCash",
            panel_metric_series(panel_rows, "eff_delta_cash"),
        )
    )
    entries.append(
        ("derived-delta", "C-Return", panel_metric_series(panel_rows, "c_return"))
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
    levels: Dict[int, Dict[str, Optional[float]]],
    factor_levels: Dict[int, Dict[str, Optional[float]]],
    panel_rows: List[Dict[str, object]],
    combined_full: List[Dict[str, object]],
    combined_recent: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    validation: List[Dict[str, object]] = []

    loaded_years = sum(1 for y in levels if EV_START_YEAR <= y <= END_YEAR)
    validation.append(
        {
            "test_name": "levels_loaded",
            "status": "PASS" if loaded_years == (END_YEAR - EV_START_YEAR + 1) else "FAIL",
            "details": f"loaded {loaded_years} years in {EV_START_YEAR}-{END_YEAR}",
        }
    )

    expected_periods = END_YEAR - EV_START_YEAR
    validation.append(
        {
            "test_name": "ev_period_count",
            "status": "PASS" if len(panel_rows) == expected_periods else "FAIL",
            "details": f"expected {expected_periods}, got {len(panel_rows)}",
        }
    )

    first = min(panel_rows, key=lambda row: int(row["from_year"]))
    validation.append(
        {
            "test_name": "first_period_is_2004_2005",
            "status": "PASS" if int(first["from_year"]) == EV_START_YEAR else "FAIL",
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

    eff_gap = 0.0
    cret_gap = 0.0
    for row in panel_rows:
        ev, price = row["EV_pct_change"], row["Price_pct_change"]
        eff, fcf, cret = row["eff_delta_cash"], row["FCF_pct_change"], row["c_return"]
        if ev is not None and price is not None and eff is not None:
            eff_gap = max(eff_gap, abs(eff - (ev - price)))
        if fcf is not None and eff is not None and cret is not None:
            cret_gap = max(cret_gap, abs(cret - (fcf - eff)))
    validation.append(
        {
            "test_name": "eff_delta_cash_identity",
            "status": "PASS" if eff_gap < 1e-9 else "FAIL",
            "details": f"max |eff - (dEV - dPrice)| = {eff_gap:.2e}",
        }
    )
    validation.append(
        {
            "test_name": "c_return_identity",
            "status": "PASS" if cret_gap < 1e-9 else "FAIL",
            "details": f"max |C-Return - (dFCF - eff)| = {cret_gap:.2e}",
        }
    )

    all_finite = all(
        row[metric] is None or math.isfinite(float(row[metric]))
        for row in panel_rows
        for metric in ("Price_pct_change", *METRICS)
    )
    validation.append(
        {
            "test_name": "all_values_finite",
            "status": "PASS" if all_finite else "FAIL",
            "details": "checked every populated metric in every period",
        }
    )

    expected_rows = len(PHASE9_FACTORS) + 3
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

    for label, table, expected_periods in (
        ("combined_full", combined_full, END_YEAR - EV_START_YEAR),
        ("combined_recent", combined_recent, END_YEAR - RECENT_START_YEAR),
    ):
        period_counts = {int(row["periods"]) for row in table}
        validation.append(
            {
                "test_name": f"{label}_periods_aligned",
                "status": "PASS"
                if period_counts == {expected_periods}
                else "FAIL",
                "details": (
                    f"expected all rows = {expected_periods} periods, "
                    f"got {sorted(period_counts)}"
                ),
            }
        )

    price_from_factors = window_stats(
        factor_pct_series(factor_levels, "Price"), EV_START_YEAR, END_YEAR
    )
    price_from_panel = window_stats(
        panel_metric_series(panel_rows, "Price_pct_change"),
        EV_START_YEAR,
        END_YEAR,
    )
    price_gap = abs(
        float(price_from_factors["mean_abs"]) - float(price_from_panel["mean_abs"])
    )
    validation.append(
        {
            "test_name": "price_series_consistent",
            "status": "PASS" if price_gap < 1e-9 else "FAIL",
            "details": (
                "Price mean_abs from Phase 9 levels vs EV panel "
                f"differ by {price_gap:.2e}"
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
                    str(row["metric"]),
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
        "# Phase 10 Enterprise Value & C-Return Summary",
        "",
        "## Testing",
        "",
        (
            "All Phase 10 validation checks passed."
            if not failing
            else "Phase 10 completed with validation FAILURES: "
            + ", ".join(row["test_name"] for row in failing)
        ),
        "",
        "Validation file: `outputs/phase10/phase10_validation_results.csv`",
        "",
        "## Method",
        "",
        "- Builds on Phase 9 levels (`outputs/phase9/phase9_factor_levels.csv`); no new data pull.",
        "- All deltas are SIMPLE year-over-year percent change, `level_t / level_t-1 - 1` (same as Phase 9).",
        "- EV is a per-share level: `EV = Price - NetCash/share`, where `NetCash/share = NetCash_total / diluted Shares`.",
        "- `eff.dCash = dEV - dPrice` (isolates the cash contribution to the value move).",
        "- `C-Return = dFCF - eff.dCash`, using total Free Cash Flow simple percent change (same FCF basis as Phase 9).",
        f"- EV depends on Price, so the panel starts with the {EV_START_YEAR}-{EV_START_YEAR + 1} period (GOOG IPO {EV_START_YEAR}).",
        "- Reported as a standalone EV panel, NOT folded into the Phase 9 seven-factor ranking/weights.",
        "",
        f"## Summary - Full History ({EV_START_YEAR}-{END_YEAR})",
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
            "The Phase 9 factors and the new EV metrics ranked together by average "
            "size of move (`mean_abs`). This is a comparison of movers only: there "
            "is deliberately NO weight column, because EV, eff.dCash, and C-Return "
            "are derived from Price, NetCash, and FCF, so folding them into the "
            "Phase 9 share-of-movement weighting would double-count. FCF appears "
            "once (as the Phase 9 factor). `type` flags each row as `factor`, "
            "`derived-level` (EV), or `derived-delta` (eff.dCash, C-Return).",
            "",
            "Both windows are recomputed on a shared basis so the numbers are "
            f"directly comparable. Full history is aligned to {EV_START_YEAR}-"
            f"{END_YEAR} (EV needs Price, which starts {EV_START_YEAR}), so these "
            "Phase 9 numbers differ from the Phase 9 2001-2025 tables by design.",
            "",
            f"### Combined - Full History ({EV_START_YEAR}-{END_YEAR})",
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
            "- `outputs/phase10/phase10_ev_levels.csv`",
            "- `outputs/phase10/phase10_ev_c_return_panel.csv`",
            "- `outputs/phase10/phase10_ev_c_return_summary_full_2004_2025.csv`",
            "- `outputs/phase10/phase10_ev_c_return_summary_recent5_2020_2025.csv`",
            "- `outputs/phase10/phase10_combined_ranking_full_2004_2025.csv`",
            "- `outputs/phase10/phase10_combined_ranking_recent5_2020_2025.csv`",
            "- `outputs/phase10/phase10_validation_results.csv`",
            "- `outputs/phase10/presentation_tables/table13_ev_c_return_summary_full_2004-2025.csv`",
            "- `outputs/phase10/presentation_tables/table14_ev_c_return_summary_recent5_2020-2025.csv`",
            "- `outputs/phase10/presentation_tables/table15_combined_ranking_full_2004-2025.csv`",
            "- `outputs/phase10/presentation_tables/table16_combined_ranking_recent5_2020-2025.csv`",
        ]
    )

    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PRESENTATION_DIR.mkdir(parents=True, exist_ok=True)

    levels = load_levels()
    factor_levels = load_factor_levels()
    ev_levels_rows = build_ev_levels_rows(levels)
    panel_rows = build_panel_rows(levels)
    full_summary = summarize(panel_rows)
    recent_summary = summarize(recent_rows(panel_rows))
    combined_full = build_combined_ranking(
        factor_levels, panel_rows, EV_START_YEAR, END_YEAR
    )
    combined_recent = build_combined_ranking(
        factor_levels, panel_rows, RECENT_START_YEAR, END_YEAR
    )
    validation_rows = build_validation_rows(
        levels, factor_levels, panel_rows, combined_full, combined_recent
    )

    write_csv(EV_LEVELS_PATH, ev_levels_rows)
    write_csv(PANEL_PATH, panel_rows)
    write_csv(FULL_SUMMARY_PATH, full_summary)
    write_csv(RECENT_SUMMARY_PATH, recent_summary)
    write_csv(COMBINED_FULL_PATH, combined_full)
    write_csv(COMBINED_RECENT_PATH, combined_recent)
    write_csv(VALIDATION_PATH, validation_rows)
    write_csv(PRES_FULL_PATH, full_summary)
    write_csv(PRES_RECENT_PATH, recent_summary)
    write_csv(PRES_COMBINED_FULL_PATH, combined_full)
    write_csv(PRES_COMBINED_RECENT_PATH, combined_recent)
    write_summary(
        full_summary, recent_summary, combined_full, combined_recent, validation_rows
    )

    for path in (
        EV_LEVELS_PATH,
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
