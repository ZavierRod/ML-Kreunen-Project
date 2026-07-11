#!/usr/bin/env python3
"""Rank and weight seven standalone factors for the GOOG ML project.

Phase 9 extends Phase 8 by adding Price as a seventh factor:

    Revenue, Net Margin, EPS, FCF, NetCash, Shares, Price

Method:

1. Rebuild the annual factor levels from `Model.csv` (2001-2025).
2. Pull year-end split-adjusted closes from Yahoo Finance (GOOG) starting 2004;
   the pricing date is the last trading day on or before 12/31 each year.
3. For each adjacent year-over-year period, compute the SIMPLE percent change
   of each factor: pct_i = level_t / level_t-1 - 1.
4. Per period, weight each factor by its absolute-share of movement among
   factors with valid data that period:
       weight_i = |pct_i| / sum_j |pct_j|      (positive, sum to 100%).
5. Rank the factors by mean absolute percent change over the full window
   and over the most recent five years.

Outputs (in outputs/phase9/):

- `phase9_factor_levels.csv`
- `phase9_seven_factor_panel.csv`
- `phase9_seven_factor_ranking_full_2001_2025.csv`
- `phase9_seven_factor_ranking_recent5_2020_2025.csv`
- `phase9_validation_results.csv`
- `phase9_summary.md`
- `presentation_tables/table11_seven_factor_ranking_full_2001-2025.csv`
- `presentation_tables/table12_seven_factor_ranking_recent5_2020-2025.csv`
- `data/goog_yahoo_year_end_prices.csv`
"""

from __future__ import annotations

import csv
import math
import statistics
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import yfinance as yf


ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT / "data" / "GOOG MS ML 10-Year Actuals" / "Model.csv"

RAW_ROWS = {
    "revenue": "Total Gross revenue (GAAP)",
    "net_income": "Net income, reported",
    "shares": "Average diluted shares",
    "free_cash_flow": "Free cash flow",
    "cash": "Cash & Cash Equivalents",
    "marketable_securities": "Marketable securities",
    "nonmarketable_equity": "Non-marketable equity securities",
    "short_term_debt": "Short-term debt",
    "long_term_debt": "Long-Term Debt",
}

NCASH_PER_SHARE_ROW = "NCash/Share"

FACTORS = ["Revenue", "Net Margin", "EPS", "FCF", "NetCash", "Shares", "Price"]

PRICE_TICKER = "GOOG"
PRICE_START_YEAR = 2004
PRICE_CACHE_PATH = ROOT / "data" / "goog_yahoo_year_end_prices.csv"

WINDOWS: List[Tuple[str, int, int]] = [
    ("2015_2025", 2015, 2025),
    ("2010_2025", 2010, 2025),
    ("2001_2025", 2001, 2025),
]

FULL_WINDOW = "2001_2025"
RECENT_WINDOW = "2015_2025"
RECENT_START_YEAR = 2020
RECENT_END_YEAR = 2025

OUTPUT_DIR = ROOT / "outputs" / "phase9"
PRESENTATION_DIR = OUTPUT_DIR / "presentation_tables"
LEVELS_PATH = OUTPUT_DIR / "phase9_factor_levels.csv"
PANEL_PATH = OUTPUT_DIR / "phase9_seven_factor_panel.csv"
FULL_RANK_PATH = OUTPUT_DIR / "phase9_seven_factor_ranking_full_2001_2025.csv"
RECENT_RANK_PATH = OUTPUT_DIR / "phase9_seven_factor_ranking_recent5_2020_2025.csv"
VALIDATION_PATH = OUTPUT_DIR / "phase9_validation_results.csv"
SUMMARY_PATH = OUTPUT_DIR / "phase9_summary.md"
PRES_FULL_PATH = PRESENTATION_DIR / "table11_seven_factor_ranking_full_2001-2025.csv"
PRES_RECENT_PATH = (
    PRESENTATION_DIR / "table12_seven_factor_ranking_recent5_2020-2025.csv"
)


def read_csv_rows(path: Path) -> List[List[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.reader(handle))


def find_row(rows: Iterable[List[str]], label: str) -> List[str]:
    for row in rows:
        if label in row:
            return row
    raise ValueError(f"Could not find row labeled {label!r}")


def annual_year_columns(model_rows: List[List[str]]) -> Dict[str, int]:
    header_row = model_rows[6]
    mapping: Dict[str, int] = {}
    for index, value in enumerate(header_row):
        if value.endswith("00:00:00"):
            mapping.setdefault(value[:4], index)
    return mapping


def to_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def load_raw_series(required_years: List[str]) -> Dict[str, Dict[str, float]]:
    model_rows = read_csv_rows(MODEL_PATH)
    year_to_col = annual_year_columns(model_rows)

    series: Dict[str, Dict[str, float]] = {}
    for name, label in RAW_ROWS.items():
        row = find_row(model_rows, label)
        series[name] = {
            year: to_float(row[year_to_col[year]]) for year in required_years
        }

    ncash_row = find_row(model_rows, NCASH_PER_SHARE_ROW)
    series["ncash_per_share_sheet"] = {}
    for year in required_years:
        cell = ncash_row[year_to_col[year]]
        if cell.strip() and to_float(cell) != 0.0:
            series["ncash_per_share_sheet"][year] = to_float(cell)

    return series


def year_end_cutoff(year: int) -> date:
    cutoff = date(year, 12, 31)
    return min(cutoff, date.today())


def fetch_yahoo_year_end_prices(
    start_year: int,
    end_year: int,
    ticker: str = PRICE_TICKER,
) -> Dict[str, Tuple[str, float]]:
    history = yf.download(
        ticker,
        start=f"{start_year}-01-01",
        end=f"{end_year + 1}-01-01",
        auto_adjust=True,
        progress=False,
    )
    if history.empty:
        raise ValueError(f"No Yahoo Finance history returned for {ticker!r}")

    close_column = "Close" if "Close" in history.columns else history.columns[0]
    prices: Dict[str, Tuple[str, float]] = {}

    for year in range(start_year, end_year + 1):
        cutoff = year_end_cutoff(year)
        year_rows = history[history.index.date <= cutoff]
        if year_rows.empty:
            continue
        last_row = year_rows.iloc[-1]
        trade_date = last_row.name.date().isoformat()
        prices[str(year)] = (trade_date, float(last_row[close_column]))

    if not prices:
        raise ValueError(
            f"No year-end prices found for {ticker!r} between {start_year} and {end_year}"
        )

    return prices


def write_price_cache(prices: Dict[str, Tuple[str, float]]) -> None:
    rows = [
        {
            "year": int(year),
            "trade_date": trade_date,
            "adjusted_close": adjusted_close,
            "ticker": PRICE_TICKER,
        }
        for year, (trade_date, adjusted_close) in sorted(
            prices.items(), key=lambda item: int(item[0])
        )
    ]
    PRICE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PRICE_CACHE_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["year", "trade_date", "adjusted_close", "ticker"],
        )
        writer.writeheader()
        writer.writerows(rows)


def load_year_end_prices(end_year: int) -> Dict[str, Tuple[str, float]]:
    prices = fetch_yahoo_year_end_prices(PRICE_START_YEAR, end_year, PRICE_TICKER)
    write_price_cache(prices)
    return prices


def net_cash(series: Dict[str, Dict[str, float]], year: str) -> float:
    return (
        series["cash"][year]
        + series["marketable_securities"][year]
        + series["nonmarketable_equity"][year]
        - series["short_term_debt"][year]
        - series["long_term_debt"][year]
    )


def factor_levels(
    series: Dict[str, Dict[str, float]],
    year: str,
    prices: Dict[str, Tuple[str, float]],
) -> Dict[str, Optional[float]]:
    revenue = series["revenue"][year]
    net_income = series["net_income"][year]
    shares = series["shares"][year]
    return {
        "Revenue": revenue,
        "Net Margin": net_income / revenue,
        "EPS": net_income / shares,
        "FCF": series["free_cash_flow"][year],
        "NetCash": net_cash(series, year),
        "Shares": shares,
        "Price": prices.get(year, (None, None))[1],
    }


def simple_pct_change(
    prev: Optional[float], cur: Optional[float]
) -> Optional[float]:
    if prev is None or cur is None or prev == 0:
        return None
    return cur / prev - 1


def build_levels_rows(
    series: Dict[str, Dict[str, float]],
    prices: Dict[str, Tuple[str, float]],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    years = sorted(
        {str(y) for _, s, e in WINDOWS for y in range(s, e + 1)}, key=int
    )
    for year in years:
        levels = factor_levels(series, year, prices)
        row: Dict[str, object] = {"year": int(year)}
        row.update({factor: levels[factor] for factor in FACTORS})
        rows.append(row)
    return rows


def absolute_share_weights(
    changes: Dict[str, Optional[float]],
) -> Dict[str, Optional[float]]:
    valid = {key: value for key, value in changes.items() if value is not None}
    total = sum(abs(value) for value in valid.values())
    weights: Dict[str, Optional[float]] = {key: None for key in changes}
    if total == 0:
        return {key: (0.0 if changes[key] is not None else None) for key in changes}
    for key, value in valid.items():
        weights[key] = abs(value) / total
    return weights


def build_panel_rows(
    series: Dict[str, Dict[str, float]],
    prices: Dict[str, Tuple[str, float]],
) -> List[Dict[str, object]]:
    panel_rows: List[Dict[str, object]] = []

    for window_label, start_year, end_year in WINDOWS:
        years = [str(y) for y in range(start_year, end_year + 1)]
        levels_by_year = {
            year: factor_levels(series, year, prices) for year in years
        }

        for index in range(1, len(years)):
            prev_year, cur_year = years[index - 1], years[index]
            prev, cur = levels_by_year[prev_year], levels_by_year[cur_year]

            pct_changes = {
                factor: simple_pct_change(prev[factor], cur[factor])
                for factor in FACTORS
            }
            weights = absolute_share_weights(pct_changes)

            row: Dict[str, object] = {
                "window_label": window_label,
                "from_year": int(prev_year),
                "to_year": int(cur_year),
                "period": f"{prev_year}-{cur_year}",
            }
            for factor in FACTORS:
                row[f"{factor}_pct_change"] = pct_changes[factor]
            for factor in FACTORS:
                row[f"{factor}_weight"] = weights[factor]
            panel_rows.append(row)

    return panel_rows


def rank_factors(
    panel_rows: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    summaries: List[Dict[str, object]] = []
    for factor in FACTORS:
        pct_values = [
            float(row[f"{factor}_pct_change"])
            for row in panel_rows
            if row[f"{factor}_pct_change"] is not None
        ]
        weight_values = [
            float(row[f"{factor}_weight"])
            for row in panel_rows
            if row[f"{factor}_weight"] is not None
        ]
        summaries.append(
            {
                "factor": factor,
                "periods": len(pct_values),
                "mean_abs_pct_change": statistics.fmean(
                    abs(v) for v in pct_values
                ),
                "mean_pct_change": statistics.fmean(pct_values),
                "mean_weight": statistics.fmean(weight_values),
                "positive_periods": sum(1 for v in pct_values if v > 0),
                "negative_periods": sum(1 for v in pct_values if v < 0),
            }
        )

    summaries.sort(key=lambda row: row["mean_abs_pct_change"], reverse=True)
    for index, row in enumerate(summaries, start=1):
        row["overall_rank"] = index
        for key in ("mean_abs_pct_change", "mean_pct_change", "mean_weight"):
            row[key] = round(float(row[key]), 6)

    ordered = [
        "overall_rank",
        "factor",
        "mean_abs_pct_change",
        "mean_weight",
        "mean_pct_change",
        "positive_periods",
        "negative_periods",
        "periods",
    ]
    return [{key: row[key] for key in ordered} for row in summaries]


def full_window_panel(panel_rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    return [row for row in panel_rows if row["window_label"] == FULL_WINDOW]


def recent_panel(panel_rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    return [
        row
        for row in panel_rows
        if row["window_label"] == RECENT_WINDOW
        and int(row["from_year"]) >= RECENT_START_YEAR
        and int(row["to_year"]) <= RECENT_END_YEAR
    ]


def build_validation_rows(
    series: Dict[str, Dict[str, float]],
    panel_rows: List[Dict[str, object]],
    end_year: int,
) -> List[Dict[str, object]]:
    validation: List[Dict[str, object]] = []

    for window_label, start_year, end_year_window in WINDOWS:
        expected_periods = end_year_window - start_year
        got = sum(1 for row in panel_rows if row["window_label"] == window_label)
        validation.append(
            {
                "test_name": f"{window_label}_period_count",
                "status": "PASS" if got == expected_periods else "FAIL",
                "details": f"expected {expected_periods}, got {got}",
            }
        )

    max_weight_gap = 0.0
    for row in panel_rows:
        active_weights = [
            float(row[f"{factor}_weight"])
            for factor in FACTORS
            if row[f"{factor}_weight"] is not None
        ]
        if active_weights:
            max_weight_gap = max(
                max_weight_gap, abs(sum(active_weights) - 1.0)
            )
    validation.append(
        {
            "test_name": "weights_sum_to_one",
            "status": "PASS" if max_weight_gap < 1e-9 else "FAIL",
            "details": f"max deviation {max_weight_gap:.12f}",
        }
    )

    all_finite = all(
        row[f"{factor}_pct_change"] is None
        or math.isfinite(float(row[f"{factor}_pct_change"]))
        for row in panel_rows
        for factor in FACTORS
    )
    validation.append(
        {
            "test_name": "all_pct_changes_finite",
            "status": "PASS" if all_finite else "FAIL",
            "details": "checked every populated factor in every period",
        }
    )

    price_periods = [
        row
        for row in panel_rows
        if row["window_label"] == FULL_WINDOW
        and row["Price_pct_change"] is not None
    ]
    expected_price_periods = end_year - PRICE_START_YEAR
    validation.append(
        {
            "test_name": "price_starts_2004",
            "status": "PASS" if len(price_periods) == expected_price_periods else "FAIL",
            "details": (
                f"expected {expected_price_periods} price periods, "
                f"got {len(price_periods)}"
            ),
        }
    )
    first_price_period = min(price_periods, key=lambda row: int(row["from_year"]))
    validation.append(
        {
            "test_name": "first_price_period_is_2004_2005",
            "status": "PASS"
            if int(first_price_period["from_year"]) == PRICE_START_YEAR
            else "FAIL",
            "details": (
                f"first price period {first_price_period['from_year']}-"
                f"{first_price_period['to_year']}"
            ),
        }
    )

    sheet = series["ncash_per_share_sheet"]
    max_ncash_gap = 0.0
    for year, sheet_value in sheet.items():
        computed = net_cash(series, year) / series["shares"][year]
        max_ncash_gap = max(max_ncash_gap, abs(computed - sheet_value))
    validation.append(
        {
            "test_name": "netcash_matches_sheet_ncash_per_share",
            "status": "PASS" if max_ncash_gap < 1e-2 else "FAIL",
            "details": (
                f"max abs gap {max_ncash_gap:.6f} over {len(sheet)} years"
            ),
        }
    )

    share_years = [str(y) for y in range(2001, end_year + 1)]
    max_ratio = max(
        series["shares"][share_years[i]] / series["shares"][share_years[i - 1]]
        for i in range(1, len(share_years))
    )
    validation.append(
        {
            "test_name": "shares_split_consistent",
            "status": "PASS" if max_ratio < 5.0 else "FAIL",
            "details": f"max adjacent share ratio {max_ratio:.3f} (split break gone if < 5)",
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


def write_summary(
    full_rank: List[Dict[str, object]],
    recent_rank: List[Dict[str, object]],
    validation_rows: List[Dict[str, object]],
) -> None:
    failing = [row for row in validation_rows if row["status"] != "PASS"]

    def rank_table(rank_rows: List[Dict[str, object]]) -> List[str]:
        return md_table(
            ["Rank", "Factor", "Mean |% change|", "Mean weight", "Mean % change"],
            [
                [
                    str(row["overall_rank"]),
                    str(row["factor"]),
                    f"{float(row['mean_abs_pct_change']) * 100:.1f}%",
                    f"{float(row['mean_weight']) * 100:.1f}%",
                    f"{float(row['mean_pct_change']) * 100:.1f}%",
                ]
                for row in rank_rows
            ],
        )

    top_full = full_rank[0]["factor"]
    top_recent = recent_rank[0]["factor"]

    lines: List[str] = [
        "# Phase 9 Seven-Factor Ranking Summary",
        "",
        "## Testing",
        "",
        (
            "All Phase 9 validation checks passed."
            if not failing
            else "Phase 9 completed with validation FAILURES: "
            + ", ".join(row["test_name"] for row in failing)
        ),
        "",
        "Validation file: `outputs/phase9/phase9_validation_results.csv`",
        "",
        "## Method",
        "",
        "- Factors ranked: Revenue, Net Margin, EPS, FCF, NetCash, Shares, Price.",
        "- Builds on Phase 8 by adding Price from Yahoo Finance.",
        "- Each factor's year-over-year SIMPLE percent change is computed per period.",
        "- Per-period weight = `|pct change_i| / sum_j |pct change_j|` over factors with valid data (positive, sum to 100%).",
        "- Factors are ranked by mean absolute percent change.",
        "- NetCash = Cash + Marketable securities + Non-marketable equity securities - Short-term debt - Long-Term Debt (matches the workbook NCash/Share row).",
        "- Diluted shares are split-consistent (pre-split 2001-2013 restated x20).",
        f"- Price = split-adjusted year-end close for `{PRICE_TICKER}` from Yahoo Finance, last trading day on or before 12/31, starting {PRICE_START_YEAR}.",
        "",
        "## Ranking - Full History (2001-2025)",
        "",
    ]
    lines.extend(rank_table(full_rank))
    lines.extend(
        [
            "",
            f"- Largest average mover (2001-2025): `{top_full}`.",
            "",
            "## Ranking - Recent 5 Years (2020-2025)",
            "",
        ]
    )
    lines.extend(rank_table(recent_rank))
    lines.extend(
        [
            "",
            f"- Largest average mover (2020-2025): `{top_recent}`.",
            "",
            "## Output Files",
            "",
            "- `outputs/phase9/phase9_factor_levels.csv`",
            "- `outputs/phase9/phase9_seven_factor_panel.csv`",
            "- `outputs/phase9/phase9_seven_factor_ranking_full_2001_2025.csv`",
            "- `outputs/phase9/phase9_seven_factor_ranking_recent5_2020_2025.csv`",
            "- `outputs/phase9/phase9_validation_results.csv`",
            "- `outputs/phase9/presentation_tables/table11_seven_factor_ranking_full_2001-2025.csv`",
            "- `outputs/phase9/presentation_tables/table12_seven_factor_ranking_recent5_2020-2025.csv`",
            "- `data/goog_yahoo_year_end_prices.csv`",
        ]
    )

    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PRESENTATION_DIR.mkdir(parents=True, exist_ok=True)

    all_years = sorted(
        {str(y) for _, s, e in WINDOWS for y in range(s, e + 1)}, key=int
    )
    end_year = int(all_years[-1])
    series = load_raw_series(all_years)
    prices = load_year_end_prices(end_year)

    levels_rows = build_levels_rows(series, prices)
    panel_rows = build_panel_rows(series, prices)
    full_rank = rank_factors(full_window_panel(panel_rows))
    recent_rank = rank_factors(recent_panel(panel_rows))
    validation_rows = build_validation_rows(series, panel_rows, end_year)

    write_csv(LEVELS_PATH, levels_rows)
    write_csv(PANEL_PATH, panel_rows)
    write_csv(FULL_RANK_PATH, full_rank)
    write_csv(RECENT_RANK_PATH, recent_rank)
    write_csv(VALIDATION_PATH, validation_rows)
    write_csv(PRES_FULL_PATH, full_rank)
    write_csv(PRES_RECENT_PATH, recent_rank)
    write_summary(full_rank, recent_rank, validation_rows)

    for path in (
        LEVELS_PATH,
        PANEL_PATH,
        FULL_RANK_PATH,
        RECENT_RANK_PATH,
        VALIDATION_PATH,
        PRES_FULL_PATH,
        PRES_RECENT_PATH,
        SUMMARY_PATH,
        PRICE_CACHE_PATH,
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
