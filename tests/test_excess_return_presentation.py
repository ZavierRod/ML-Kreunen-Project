import unittest

import pandas as pd

from ui.excess_return_engine.presentation import (
    company_options,
    configuration_quality,
    factor_option_label,
    predictive_strength_label,
)


class PresentationTests(unittest.TestCase):
    def test_company_options_use_permanent_identifier(self) -> None:
        inference = pd.DataFrame(
            [
                {"permno": 2, "ticker": "BBB", "company": "Beta"},
                {"permno": 1, "ticker": "AAA", "company": "Alpha"},
            ]
        )

        options = company_options(inference)

        self.assertEqual(
            options,
            [
                ("AAA · Alpha · PERMNO 1", 1),
                ("BBB · Beta · PERMNO 2", 2),
            ],
        )

    def test_configuration_quality_blocks_missing_current_factors(self) -> None:
        months = pd.date_range("2015-01-31", periods=120, freq="ME")
        training = pd.DataFrame(
            {
                "month_end": months,
                "size": 1.0,
                "momentum_12_1": 0.1,
                "excess_return_next_month": 0.01,
            }
        )
        inference = pd.DataFrame(
            [
                {
                    "permno": 1,
                    "size": 1.0,
                    "momentum_12_1": pd.NA,
                }
            ]
        )

        quality = configuration_quality(
            training,
            inference,
            1,
            ("size", "momentum_12_1"),
        )

        self.assertEqual(quality["status"], "blocked")
        self.assertEqual(quality["current_completeness"], 0.5)

    def test_factor_labels_and_predictive_strength_are_explicit(self) -> None:
        self.assertEqual(factor_option_label("size"), "Size · Market")
        self.assertEqual(
            predictive_strength_label(
                {"oos_r2_vs_zero": 0.002, "directional_hit_rate": 0.50}
            ),
            "Modest",
        )


if __name__ == "__main__":
    unittest.main()
