import unittest

import numpy as np
import pandas as pd

from excess_return_engine.model import (
    ForecastRequest,
    _empirical_probability_positive,
    generate_forecast,
)


def synthetic_panels() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(7)
    months = pd.date_range("2015-01-31", periods=96, freq="ME")
    rows = []
    for month_index, month in enumerate(months[:-1]):
        for permno in range(1, 9):
            size = permno / 10 + month_index / 500
            momentum = np.sin(month_index / 8 + permno) / 10
            target = 0.04 * size + 0.30 * momentum + rng.normal(0, 0.01)
            rows.append(
                {
                    "permno": permno,
                    "month_end": month,
                    "target_month": month + pd.offsets.MonthEnd(1),
                    "benchmark_id": "test-benchmark",
                    "ticker": f"T{permno}",
                    "company": f"Company {permno}",
                    "size": size,
                    "momentum_12_1": momentum,
                    "excess_return_next_month": target,
                }
            )
    training = pd.DataFrame(rows)
    inference_month = months[-1]
    inference = pd.DataFrame(
        [
            {
                "permno": permno,
                "month_end": inference_month,
                "target_month": inference_month + pd.offsets.MonthEnd(1),
                "benchmark_id": "test-benchmark",
                "ticker": f"T{permno}",
                "company": f"Company {permno}",
                "size": permno / 10 + len(months) / 500,
                "momentum_12_1": np.sin(len(months) / 8 + permno) / 10,
            }
            for permno in range(1, 9)
        ]
    )
    return training, inference


class ForecastTests(unittest.TestCase):
    def test_empirical_probability_does_not_require_an_outer_matrix(self) -> None:
        predictions = np.array([-0.05, 0.00, 0.05])
        residuals = np.array([-0.02, 0.01, 0.10])

        probabilities = _empirical_probability_positive(predictions, residuals)

        np.testing.assert_allclose(probabilities, [1 / 3, 2 / 3, 1.0])

    def test_forecast_uses_selected_factors_and_reconciles_contributions(self) -> None:
        training, inference = synthetic_panels()
        request = ForecastRequest(
            permno=3,
            selected_factors=("size", "momentum_12_1"),
            tuning_months=6,
            calibration_months=12,
            minimum_training_months=48,
            alpha_grid=(0.0001,),
            l1_ratio_grid=(0.5,),
        )

        result = generate_forecast(training, inference, request)

        self.assertEqual(result.permno, 3)
        self.assertEqual(result.selected_factors, ("size", "momentum_12_1"))
        self.assertEqual(
            {item.factor_id for item in result.contributions},
            {"size", "momentum_12_1"},
        )
        reconciled = result.intercept + sum(
            item.contribution for item in result.contributions
        )
        self.assertAlmostEqual(reconciled, result.expected_excess_return)
        self.assertLess(result.interval_lower, result.interval_upper)
        self.assertGreaterEqual(result.probability_positive, 0)
        self.assertLessEqual(result.probability_positive, 1)
        self.assertEqual(result.data_quality["selected_factor_completeness"], 1.0)
        self.assertIn("interval_coverage", result.validation_metrics)

    def test_forecast_requires_enough_history(self) -> None:
        training, inference = synthetic_panels()
        request = ForecastRequest(
            permno=3,
            selected_factors=("size",),
            minimum_training_months=100,
        )

        with self.assertRaisesRegex(ValueError, "historical months"):
            generate_forecast(training, inference, request)


if __name__ == "__main__":
    unittest.main()
