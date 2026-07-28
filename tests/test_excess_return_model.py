import unittest

import numpy as np
import pandas as pd

from excess_return_engine.evidence import (
    classify_factor_regimes,
    find_similar_conditions,
)
from excess_return_engine.challengers import CHALLENGER_VERSION
from excess_return_engine.model import (
    ForecastRequest,
    _empirical_probability_positive,
    generate_forecast,
)
from excess_return_engine.reliability import RELIABILITY_VERSION
from excess_return_engine.validation import VALIDATION_VERSION


def synthetic_panels() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(7)
    months = pd.date_range("2015-01-31", periods=96, freq="ME")
    rows = []
    for month_index, month in enumerate(months[:-1]):
        for permno in range(1, 9):
            size = permno / 10 + month_index / 500
            momentum = np.sin(month_index / 8 + permno) / 10
            target = 0.04 * size + 0.30 * momentum + rng.normal(0, 0.01)
            benchmark_return = 0.005
            rows.append(
                {
                    "permno": permno,
                    "month_end": month,
                    "target_month": month + pd.offsets.MonthEnd(1),
                    "benchmark_id": "test-benchmark",
                    "ticker": f"T{permno}",
                    "company": f"Company {permno}",
                    "size": size,
                    "market_cap": float(np.exp(size)),
                    "momentum_12_1": momentum,
                    "source_last_trading_date": month,
                    "stock_return_next_month": target + benchmark_return,
                    "benchmark_return": benchmark_return,
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
                "market_cap": float(
                    np.exp(permno / 10 + len(months) / 500)
                ),
                "momentum_12_1": np.sin(len(months) / 8 + permno) / 10,
                "source_last_trading_date": inference_month,
                "stock_return_next_month": np.nan,
                "benchmark_return": np.nan,
                "excess_return_next_month": np.nan,
            }
            for permno in range(1, 9)
        ]
    )
    return training, inference


class ForecastTests(unittest.TestCase):
    def test_regimes_are_explicit_cross_sectional_buckets(self) -> None:
        regimes = classify_factor_regimes(
            ("size", "momentum_12_1"),
            np.array([0.8, -0.8]),
        )

        self.assertEqual(regimes[0].regime, "Top quintile")
        self.assertEqual(regimes[0].percentile, 0.9)
        self.assertEqual(regimes[1].regime, "Bottom quintile")
        self.assertAlmostEqual(regimes[1].percentile, 0.1)

    def test_historical_evidence_uses_nearest_normalized_rows(self) -> None:
        historical = pd.DataFrame(
            [
                {
                    "permno": 1,
                    "month_end": "2024-01-31",
                    "size": 0.10,
                    "momentum_12_1": 0.10,
                    "excess_return_next_month": 0.03,
                },
                {
                    "permno": 2,
                    "month_end": "2024-01-31",
                    "size": 0.90,
                    "momentum_12_1": 0.90,
                    "excess_return_next_month": -0.02,
                },
                {
                    "permno": 3,
                    "month_end": "2024-02-29",
                    "size": 0.20,
                    "momentum_12_1": 0.20,
                    "excess_return_next_month": 0.01,
                },
            ]
        )

        evidence = find_similar_conditions(
            historical,
            ("size", "momentum_12_1"),
            np.array([0.0, 0.0]),
            neighbor_count=2,
            target_column="excess_return_next_month",
        )

        self.assertEqual(
            [analog.permno for analog in evidence.analogs],
            [1, 3],
        )
        self.assertAlmostEqual(evidence.mean_excess_return, 0.02)
        self.assertEqual(evidence.probability_positive, 1.0)

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
        self.assertIsNone(result.training_window_months)
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
        self.assertEqual(len(result.current_regime), 2)
        self.assertEqual(result.historical_evidence.neighbor_count, 20)
        self.assertEqual(len(result.historical_evidence.analogs), 20)
        self.assertGreaterEqual(result.reliability.model_reliability_score, 0)
        self.assertLessEqual(result.reliability.model_reliability_score, 100)
        self.assertEqual(result.reliability_version, RELIABILITY_VERSION)
        self.assertEqual(result.validation_version, VALIDATION_VERSION)
        self.assertEqual(result.challenger_version, CHALLENGER_VERSION)
        self.assertEqual(len(result.challenger_diagnostics.metrics), 5)
        self.assertTrue(
            all(
                item.evaluation_rows
                == result.validation_metrics["evaluation_rows"]
                for item in result.challenger_diagnostics.metrics
            )
        )
        self.assertEqual(len(result.validation_diagnostics.calibration_bins), 10)
        self.assertGreaterEqual(len(result.validation_diagnostics.yearly_metrics), 1)

    def test_forecast_requires_enough_history(self) -> None:
        training, inference = synthetic_panels()
        request = ForecastRequest(
            permno=3,
            selected_factors=("size",),
            minimum_training_months=100,
        )

        with self.assertRaisesRegex(ValueError, "historical months"):
            generate_forecast(training, inference, request)

    def test_forecast_uses_requested_trailing_training_window(self) -> None:
        training, inference = synthetic_panels()
        inference.attrs["snapshot_source"] = "historical_replay"
        request = ForecastRequest(
            permno=3,
            selected_factors=("size",),
            training_window_months=72,
            tuning_months=6,
            calibration_months=12,
            minimum_training_months=48,
            alpha_grid=(0.0001,),
            l1_ratio_grid=(0.5,),
        )

        result = generate_forecast(training, inference, request)

        self.assertEqual(result.training_window_months, 72)
        self.assertEqual(result.snapshot_source, "historical_replay")
        self.assertEqual(result.replay_version, "historical-replay-v1")
        self.assertEqual(result.data_quality["training_months"], 72)
        self.assertIn("months-2016-12-31-to-2022-11-30", result.data_version)

    def test_training_window_must_cover_model_splits(self) -> None:
        training, inference = synthetic_panels()
        request = ForecastRequest(
            permno=3,
            selected_factors=("size",),
            training_window_months=71,
            tuning_months=6,
            calibration_months=12,
            minimum_training_months=54,
        )

        with self.assertRaisesRegex(ValueError, "at least 72 months"):
            generate_forecast(training, inference, request)

    def test_training_window_cannot_exceed_available_history(self) -> None:
        training, inference = synthetic_panels()
        request = ForecastRequest(
            permno=3,
            selected_factors=("size",),
            training_window_months=96,
            tuning_months=6,
            calibration_months=12,
            minimum_training_months=48,
        )

        with self.assertRaisesRegex(ValueError, "only 95 are available"):
            generate_forecast(training, inference, request)


if __name__ == "__main__":
    unittest.main()
