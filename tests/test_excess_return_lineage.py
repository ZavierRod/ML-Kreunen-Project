import unittest

import pandas as pd

from excess_return_engine.lineage import (
    LINEAGE_VERSION,
    assess_factor_lineage,
)


def current_row() -> pd.Series:
    return pd.Series(
        {
            "month_end": "2025-12-31",
            "source_last_trading_date": "2025-12-31",
            "datadate": "2024-12-31",
            "fund_available_date": "2025-03-31",
            "asset_growth": 0.12,
            "size": 14.4,
            "market_cap": 1_800_000.0,
        }
    )


class FactorLineageTests(unittest.TestCase):
    def test_traces_market_and_fundamental_factor_sources(self) -> None:
        assessment = assess_factor_lineage(
            current_row(),
            ("asset_growth", "size"),
            "2025-12-31",
            normalized_values={
                "asset_growth": 0.2,
                "size": 0.9,
            },
            source_snapshot="data-v1",
        )

        self.assertEqual(assessment.version, LINEAGE_VERSION)
        self.assertEqual(assessment.status, "Research lag proxy")
        self.assertEqual(assessment.research_proxy_factor_count, 1)
        fundamentals, market = assessment.factors
        self.assertEqual(fundamentals.period_end_date, "2024-12-31")
        self.assertEqual(fundamentals.available_at, "2025-03-31")
        self.assertEqual(fundamentals.availability_lag_days, 90)
        self.assertEqual(fundamentals.freshness_status, "Current")
        self.assertEqual(market.observation_date, "2025-12-31")
        self.assertEqual(market.freshness_status, "Current")

    def test_future_dated_fundamental_source_is_blocked(self) -> None:
        row = current_row()
        row["fund_available_date"] = "2026-03-31"

        with self.assertRaisesRegex(
            ValueError,
            "not available by the forecast as-of date",
        ):
            assess_factor_lineage(
                row,
                ("asset_growth",),
                "2025-12-31",
            )

    def test_missing_source_is_visible_without_strict_mode(self) -> None:
        row = current_row().drop("market_cap")

        assessment = assess_factor_lineage(
            row,
            ("size",),
            "2025-12-31",
            strict=False,
        )

        self.assertEqual(assessment.status, "Incomplete")
        self.assertEqual(assessment.incomplete_factor_count, 1)
        self.assertIn("Missing source columns", assessment.warnings[0])

    def test_malformed_source_date_is_incomplete(self) -> None:
        row = current_row()
        row["source_last_trading_date"] = "not-a-date"

        assessment = assess_factor_lineage(
            row,
            ("size",),
            "2025-12-31",
            strict=False,
        )

        self.assertEqual(assessment.status, "Incomplete")
        self.assertIn(
            "Required source dates are unavailable",
            " ".join(assessment.warnings),
        )

    def test_old_fundamental_period_is_marked_stale(self) -> None:
        row = current_row()
        row["datadate"] = "2023-12-31"
        row["fund_available_date"] = "2024-03-31"

        assessment = assess_factor_lineage(
            row,
            ("asset_growth",),
            "2025-12-31",
        )

        self.assertEqual(assessment.status, "Stale")
        self.assertEqual(assessment.freshness_score, 0.0)
        self.assertEqual(assessment.stale_factor_count, 1)


if __name__ == "__main__":
    unittest.main()
