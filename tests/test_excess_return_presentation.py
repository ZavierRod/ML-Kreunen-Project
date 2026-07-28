import unittest
from types import SimpleNamespace

import pandas as pd

from ui.excess_return_engine.presentation import (
    company_options,
    configuration_quality,
    correlation_warning_table,
    factor_option_label,
    historical_analog_table,
    predictive_strength_label,
    reliability_component_table,
    regime_summary,
    regime_table,
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

    def test_configuration_quality_flags_correlated_selected_factors(self) -> None:
        months = pd.date_range("2015-01-31", periods=120, freq="ME")
        training = pd.DataFrame(
            {
                "month_end": months,
                "size": range(120),
                "momentum_12_1": range(120),
                "excess_return_next_month": 0.01,
            }
        )
        inference = pd.DataFrame(
            [{"permno": 1, "size": 1.0, "momentum_12_1": 1.0}]
        )

        quality = configuration_quality(
            training,
            inference,
            1,
            ("size", "momentum_12_1"),
        )

        self.assertEqual(len(quality["correlated_pairs"]), 1)

    def test_factor_labels_and_predictive_strength_are_explicit(self) -> None:
        self.assertEqual(factor_option_label("size"), "Size · Market")
        self.assertEqual(
            predictive_strength_label(
                {"oos_r2_vs_zero": 0.002, "directional_hit_rate": 0.50}
            ),
            "Modest",
        )

    def test_regime_and_analog_tables_are_readable(self) -> None:
        result = SimpleNamespace(
            current_regime=(
                SimpleNamespace(
                    factor_id="size",
                    normalized_value=0.8,
                    percentile=0.9,
                    regime="Top quintile",
                ),
                SimpleNamespace(
                    factor_id="momentum_12_1",
                    normalized_value=-0.6,
                    percentile=0.2,
                    regime="Bottom quintile",
                ),
            ),
            historical_evidence=SimpleNamespace(
                analogs=(
                    SimpleNamespace(
                        ticker="AAA",
                        company="Alpha",
                        month_end="2024-01-31",
                        target_month="2024-02-29",
                        similarity=0.95,
                        observed_excess_return=0.02,
                    ),
                )
            ),
        )

        self.assertEqual(
            regime_summary(result),
            "Top quintile Size · Bottom quintile 12-1 momentum",
        )
        self.assertEqual(regime_table(result).iloc[0]["Factor"], "Size")
        self.assertEqual(historical_analog_table(result).iloc[0]["Ticker"], "AAA")

    def test_reliability_tables_expose_components_and_correlations(self) -> None:
        result = SimpleNamespace(
            reliability=SimpleNamespace(
                components=(
                    SimpleNamespace(
                        component="Interval calibration",
                        score=92.0,
                        status="Strong",
                        value="79% realized",
                        detail="Coverage definition.",
                    ),
                ),
                correlated_factor_pairs=(
                    SimpleNamespace(
                        factor_a="size",
                        factor_b="momentum_12_1",
                        correlation=0.88,
                    ),
                ),
            )
        )

        self.assertEqual(
            reliability_component_table(result).iloc[0]["Status"],
            "Strong",
        )
        self.assertEqual(
            correlation_warning_table(result).iloc[0]["Factor A"],
            "Size",
        )


if __name__ == "__main__":
    unittest.main()
