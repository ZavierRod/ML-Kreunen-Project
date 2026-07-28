import unittest

import numpy as np
import pandas as pd

from excess_return_engine.monthly import (
    LAST_VALUE_COLUMNS,
    aggregate_daily_chunk,
    combine_monthly_fragments,
)


def daily_row(
    permno: int,
    date: str,
    daily_return: float,
    price: float = 10.0,
    ticker: str = "TEST",
    market_cap: float = 100.0,
) -> dict:
    row = {
        "permno": permno,
        "dlycaldt": date,
        "dlyret": daily_return,
        "dlyprc": price,
        "gvkey": 1000 + permno,
        "company": f"Company {permno}",
        "ticker": ticker,
        "dlyvol": 1_000.0,
        "market_cap": market_cap,
        "datadate": "2023-12-31",
        "fund_available_date": "2024-03-31",
        "ceq": 50.0,
        "momentum_12_1": 0.10,
        "volatility_21d": 0.20,
        "liquidity_21d": 10_000.0,
        "asset_growth": 0.05,
        "leverage": 0.40,
        "profit_margin": 0.15,
        "roe": 0.12,
        "ev": 125.0,
        "ev_ebitda": 8.0,
    }
    assert set(LAST_VALUE_COLUMNS).issubset(row)
    return row


class DailyAggregationTests(unittest.TestCase):
    def test_compounds_returns_and_retains_final_month(self) -> None:
        daily = pd.DataFrame(
            [
                daily_row(1, "2024-01-30", 0.10, market_cap=100),
                daily_row(1, "2024-01-31", -0.05, market_cap=105),
                daily_row(1, "2024-02-29", 0.20, market_cap=126),
            ]
        )

        fragment = aggregate_daily_chunk(daily)
        monthly = combine_monthly_fragments([fragment], min_trading_days=1)

        self.assertEqual(monthly["month"].tolist(), ["2024-01", "2024-02"])
        self.assertAlmostEqual(monthly.iloc[0]["ret_m"], (1.10 * 0.95) - 1)
        self.assertAlmostEqual(monthly.iloc[1]["ret_m"], 0.20)
        self.assertEqual(monthly.iloc[1]["market_cap"], 126)
        self.assertNotIn("y_next", monthly.columns)

    def test_combines_month_split_across_source_row_groups(self) -> None:
        first = aggregate_daily_chunk(
            pd.DataFrame([daily_row(1, "2024-01-30", 0.10, ticker="OLD")])
        )
        second = aggregate_daily_chunk(
            pd.DataFrame([daily_row(1, "2024-01-31", 0.20, ticker="NEW")])
        )

        monthly = combine_monthly_fragments(
            [first, second],
            min_trading_days=1,
        )

        self.assertEqual(len(monthly), 1)
        self.assertEqual(monthly.iloc[0]["n_days"], 2)
        self.assertAlmostEqual(monthly.iloc[0]["ret_m"], (1.10 * 1.20) - 1)
        self.assertEqual(monthly.iloc[0]["ticker"], "NEW")
        self.assertEqual(
            monthly.iloc[0]["source_last_trading_date"],
            pd.Timestamp("2024-01-31"),
        )

    def test_filters_low_prices_missing_returns_and_short_months(self) -> None:
        daily = pd.DataFrame(
            [
                daily_row(1, "2024-01-29", 0.01, price=4.99),
                daily_row(1, "2024-01-30", np.nan, price=10.0),
                daily_row(1, "2024-01-31", 0.02, price=10.0),
            ]
        )

        fragment = aggregate_daily_chunk(daily, min_price=5.0)
        included = combine_monthly_fragments([fragment], min_trading_days=1)
        excluded = combine_monthly_fragments([fragment], min_trading_days=2)

        self.assertEqual(included.iloc[0]["n_days"], 1)
        self.assertAlmostEqual(included.iloc[0]["ret_m"], 0.02)
        self.assertTrue(excluded.empty)


if __name__ == "__main__":
    unittest.main()
