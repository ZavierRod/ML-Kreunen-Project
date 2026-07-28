import unittest

import numpy as np
import pandas as pd

from excess_return_engine.features import (
    FACTOR_IDS,
    FEATURE_VERSION,
    build_factor_panel,
    rank_normalize_factors,
    ranked_factor_column,
    validate_factor_selection,
)


def monthly_row(
    permno: int,
    month: str,
    monthly_return: float,
    market_cap: float = 100.0,
    fund_available_date: str = "2023-03-31",
) -> dict:
    return {
        "permno": permno,
        "month_end": month,
        "ret_m": monthly_return,
        "log_ret_m": np.log1p(monthly_return),
        "market_cap": market_cap,
        "ceq": 50.0,
        "fund_available_date": fund_available_date,
        "momentum_12_1": 0.10,
        "volatility_21d": 0.20 + permno * 0.01,
        "liquidity_21d": 10.0,
        "asset_growth": 0.05,
        "leverage": 0.40,
        "profit_margin": 0.15,
        "roe": 0.12,
        "ev_ebitda": 8.0,
    }


class FactorPanelTests(unittest.TestCase):
    def test_builds_registered_factors_and_quality_fields(self) -> None:
        monthly = pd.DataFrame(
            [
                monthly_row(1, "2024-01-31", 0.01),
                monthly_row(1, "2024-02-29", 0.02),
                monthly_row(2, "2024-02-29", -0.01, market_cap=200),
            ]
        )

        factors = build_factor_panel(monthly)

        self.assertTrue(set(FACTOR_IDS).issubset(factors.columns))
        self.assertTrue((factors["feature_version"] == FEATURE_VERSION).all())
        self.assertAlmostEqual(factors.iloc[0]["size"], np.log(100))
        self.assertAlmostEqual(factors.iloc[0]["book_to_market"], 0.5)
        self.assertAlmostEqual(factors.iloc[0]["return_1m"], 0.01)
        february = factors[factors["month_end"] == pd.Timestamp("2024-02-29")]
        self.assertAlmostEqual(february["relative_volatility"].sum(), 0.0)
        self.assertTrue(factors["factor_completeness"].between(0, 1).all())
        self.assertTrue(
            set(ranked_factor_column(factor) for factor in FACTOR_IDS).issubset(
                factors.columns
            )
        )

    def test_momentum_does_not_cross_a_missing_calendar_month(self) -> None:
        months = pd.date_range("2024-01-31", periods=8, freq="ME")
        complete = [
            monthly_row(1, month, 0.01)
            for month in months
        ]
        missing_april = [
            monthly_row(2, month, 0.01)
            for month in months
            if month != pd.Timestamp("2024-04-30")
        ]

        factors = build_factor_panel(pd.DataFrame(complete + missing_april))
        august = factors[factors["month_end"] == pd.Timestamp("2024-08-31")]
        complete_value = august.loc[august["permno"] == 1, "momentum_6_1"].iloc[0]
        gap_value = august.loc[august["permno"] == 2, "momentum_6_1"].iloc[0]

        self.assertAlmostEqual(complete_value, (1.01**5) - 1)
        self.assertAlmostEqual(gap_value, (1.01**4) - 1)

    def test_unavailable_fundamentals_are_masked(self) -> None:
        monthly = pd.DataFrame(
            [
                monthly_row(
                    1,
                    "2024-01-31",
                    0.01,
                    fund_available_date="2024-03-31",
                )
            ]
        )

        factors = build_factor_panel(monthly)

        for factor in [
            "asset_growth",
            "leverage",
            "profit_margin",
            "roe",
            "ev_ebitda",
            "book_to_market",
        ]:
            self.assertTrue(pd.isna(factors.iloc[0][factor]))

    def test_rank_normalization_is_cross_sectional_and_imputes_median(self) -> None:
        panel = pd.DataFrame(
            [
                {"month_end": "2024-01-31", "size": 1.0},
                {"month_end": "2024-01-31", "size": 2.0},
                {"month_end": "2024-01-31", "size": np.nan},
            ]
        )

        ranked = rank_normalize_factors(panel, ["size"])

        self.assertEqual(ranked["size"].tolist(), [0.0, 1.0, 0.0])


class FactorSelectionTests(unittest.TestCase):
    def test_rejects_unknown_and_duplicate_factors(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown factors"):
            validate_factor_selection(["not_a_factor"])
        with self.assertRaisesRegex(ValueError, "duplicates"):
            validate_factor_selection(["size", "size"])


if __name__ == "__main__":
    unittest.main()
