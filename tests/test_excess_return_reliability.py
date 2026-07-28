import unittest

import numpy as np
import pandas as pd

from excess_return_engine.reliability import (
    _coefficient_stability,
    assess_reliability,
)


class ReliabilityTests(unittest.TestCase):
    def test_coefficient_stability_handles_equal_and_reversed_vectors(self) -> None:
        self.assertEqual(
            _coefficient_stability(np.array([1.0, 2.0]), np.array([1.0, 2.0])),
            1.0,
        )
        self.assertEqual(
            _coefficient_stability(np.array([1.0]), np.array([-1.0])),
            0.0,
        )

    def test_assessment_exposes_distribution_and_correlation_warnings(self) -> None:
        rng = np.random.default_rng(2)
        first = rng.normal(0, 0.15, 200)
        historical = pd.DataFrame(
            {
                "size": first,
                "momentum_12_1": first * 0.99 + rng.normal(0, 0.001, 200),
            }
        )
        assessment = assess_reliability(
            historical=historical,
            selected_factors=("size", "momentum_12_1"),
            normalized_values=np.array([0.95, 0.95]),
            validation_metrics={
                "oos_r2_vs_zero": -0.01,
                "brier_score": 0.26,
                "brier_baseline": 0.25,
                "interval_coverage": 0.50,
            },
            interval_level=0.80,
            calibration_coefficients=np.array([0.1, 0.1]),
            final_coefficients=np.array([0.1, -0.1]),
            selected_factor_completeness=1.0,
            historical_factor_coverage=0.95,
            training_months=120,
            point_in_time_status="research_lag_proxy",
            analog_similarities=(0.80, 0.78),
        )

        self.assertEqual(
            assessment.current_distance_status,
            "Outside typical training range",
        )
        self.assertEqual(len(assessment.correlated_factor_pairs), 1)
        self.assertLess(assessment.model_reliability_score, 40)
        self.assertEqual(assessment.data_quality_score, 79.0)
        self.assertGreaterEqual(len(assessment.warnings), 5)

    def test_strong_inputs_produce_high_reliability(self) -> None:
        rng = np.random.default_rng(3)
        historical = pd.DataFrame(
            {
                "size": rng.uniform(-1, 1, 500),
                "momentum_12_1": rng.uniform(-1, 1, 500),
            }
        )
        assessment = assess_reliability(
            historical=historical,
            selected_factors=("size", "momentum_12_1"),
            normalized_values=np.array([0.0, 0.0]),
            validation_metrics={
                "oos_r2_vs_zero": 0.04,
                "brier_score": 0.18,
                "brier_baseline": 0.25,
                "interval_coverage": 0.80,
            },
            interval_level=0.80,
            calibration_coefficients=np.array([0.1, 0.2]),
            final_coefficients=np.array([0.1, 0.2]),
            selected_factor_completeness=1.0,
            historical_factor_coverage=1.0,
            training_months=150,
            point_in_time_status="verified",
            analog_similarities=(0.99,) * 12,
        )

        self.assertEqual(assessment.model_reliability_label, "High")
        self.assertEqual(assessment.data_quality_label, "High")
        self.assertEqual(assessment.warnings, ())

    def test_stale_lineage_caps_data_quality(self) -> None:
        rng = np.random.default_rng(4)
        historical = pd.DataFrame({"size": rng.uniform(-1, 1, 200)})

        assessment = assess_reliability(
            historical=historical,
            selected_factors=("size",),
            normalized_values=np.array([0.0]),
            validation_metrics={
                "oos_r2_vs_zero": 0.04,
                "brier_score": 0.18,
                "brier_baseline": 0.25,
                "interval_coverage": 0.80,
            },
            interval_level=0.80,
            calibration_coefficients=np.array([0.1]),
            final_coefficients=np.array([0.1]),
            selected_factor_completeness=1.0,
            historical_factor_coverage=1.0,
            training_months=150,
            point_in_time_status="verified",
            analog_similarities=(0.99,) * 12,
            factor_freshness_score=0.0,
            factor_lineage_status="Stale",
        )

        self.assertEqual(assessment.data_quality_score, 59.0)
        self.assertIn("stale source evidence", " ".join(assessment.warnings))


if __name__ == "__main__":
    unittest.main()
