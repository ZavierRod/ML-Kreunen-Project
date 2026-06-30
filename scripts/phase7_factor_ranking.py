#!/usr/bin/env python3
"""Build aggregate factor-ranking tables for the Phase 7 presentation.

Ranks the decomposition factors over the full 2001-2025 window by their
average importance (mean absolute log contribution). The diluted-share basis is
now consistent across all years (the pre-split 2001-2013 share counts have been
restated x20), so every period is included in the ranking metric.

Two tables are written to outputs/phase7/presentation_tables/:

- `table7_fcf_factor_ranking_2001-2025.csv` (the 3 FCF factors)
- `table8_all_six_factor_ranking_2001-2025.csv` (EPS trio + FCF trio)
"""

from __future__ import annotations

import csv
import statistics
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parent.parent
PHASE7_DIR = ROOT / "outputs" / "phase7"
THREE_FACTOR_PATH = PHASE7_DIR / "phase7_fcf_three_factor_decomposition.csv"
COMBINED_PATH = PHASE7_DIR / "phase7_combined_six_factor_panel.csv"
OUTPUT_DIR = PHASE7_DIR / "presentation_tables"
FCF_RANK_PATH = OUTPUT_DIR / "table7_fcf_factor_ranking_2001-2025.csv"
SIX_RANK_PATH = OUTPUT_DIR / "table8_all_six_factor_ranking_2001-2025.csv"

WINDOW = "2001_2025"


def read_window(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    return [row for row in rows if row["window_label"] == WINDOW]


def summarise(label: str, contributions: List[float],
              rank1_count: int = 0) -> Dict[str, object]:
    return {
        "factor": label,
        "times_rank_1": rank1_count,
        "positive_periods": sum(1 for v in contributions if v > 0),
        "negative_periods": sum(1 for v in contributions if v < 0),
        "mean_contribution": statistics.fmean(contributions),
        "mean_abs_contribution": statistics.fmean(
            abs(v) for v in contributions
        ),
    }


def write_ranked(
    path: Path, summaries: List[Dict[str, object]], include_rank_1: bool = True
) -> None:
    summaries.sort(
        key=lambda row: row["mean_abs_contribution"], reverse=True
    )
    for index, row in enumerate(summaries, start=1):
        row["overall_rank"] = index
        for key in (
            "mean_contribution",
            "mean_abs_contribution",
        ):
            row[key] = round(row[key], 4)

    fieldnames = [
        "overall_rank",
        "factor",
        "mean_abs_contribution",
        "mean_contribution",
        "positive_periods",
        "negative_periods",
    ]
    if include_rank_1:
        fieldnames.append("times_rank_1")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in summaries:
            writer.writerow({key: row[key] for key in fieldnames})


def build_fcf_ranking() -> None:
    rows = read_window(THREE_FACTOR_PATH)

    factor_keys = {
        "Revenue": "revenue_log_contribution",
        "FCF Margin": "fcf_margin_log_contribution",
        "Share Count": "share_count_log_contribution",
    }
    rank1_counts = {
        "Revenue": sum(1 for r in rows if r["rank_1_factor"] == "revenue"),
        "FCF Margin": sum(1 for r in rows if r["rank_1_factor"] == "fcf_margin"),
        "Share Count": sum(1 for r in rows if r["rank_1_factor"] == "share_count"),
    }

    summaries = [
        summarise(
            label,
            [float(row[key]) for row in rows],
            rank1_counts[label],
        )
        for label, key in factor_keys.items()
    ]
    write_ranked(FCF_RANK_PATH, summaries)


def build_six_factor_ranking() -> None:
    rows = read_window(COMBINED_PATH)

    factor_keys = {
        "EPS: Revenue": "eps_revenue_log_contribution",
        "EPS: Net Margin": "eps_net_margin_log_contribution",
        "EPS: Share Count": "eps_share_count_log_contribution",
        "FCF: Revenue": "fcf_revenue_log_contribution",
        "FCF: FCF Margin": "fcf_margin_log_contribution",
        "FCF: Share Count": "fcf_share_count_log_contribution",
    }

    summaries = [
        summarise(label, [float(row[key]) for row in rows])
        for label, key in factor_keys.items()
    ]
    write_ranked(SIX_RANK_PATH, summaries, include_rank_1=False)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    build_fcf_ranking()
    build_six_factor_ranking()
    print(f"Wrote {FCF_RANK_PATH.relative_to(ROOT)}")
    print(f"Wrote {SIX_RANK_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
