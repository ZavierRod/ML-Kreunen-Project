import unittest

import numpy as np
import pandas as pd

from excess_return_engine.validation import build_validation_diagnostics


class ValidationDiagnosticsTests(unittest.TestCase):
    def test_probability_bins_and_yearly_metrics_are_auditable(self) -> None:
        validation = pd.DataFrame(
            {
                "month_end": pd.to_datetime(
                    [
                        "2023-11-30",
                        "2023-12-31",
                        "2024-01-31",
                        "2024-02-29",
                    ]
                ),
                "target_month": pd.to_datetime(
                    [
                        "2023-12-31",
                        "2024-01-31",
                        "2024-02-29",
                        "2024-03-31",
                    ]
                ),
                "target": [0.02, -0.01, 0.04, -0.03],
            }
        )
        diagnostics = build_validation_diagnostics(
            validation=validation,
            predictions=np.array([0.01, 0.00, 0.03, -0.01]),
            probabilities=np.array([0.7, 0.4, 0.8, 0.3]),
            residual_bounds=(-0.03, 0.03),
            target_column="target",
            month_column="month_end",
            bin_count=2,
        )

        self.assertEqual(len(diagnostics.calibration_bins), 2)
        self.assertEqual(
            sum(item.rows for item in diagnostics.calibration_bins),
            4,
        )
        self.assertEqual(
            [item.outcome_year for item in diagnostics.yearly_metrics],
            [2023, 2024],
        )
        self.assertEqual(diagnostics.yearly_metrics[0].rows, 1)
        self.assertAlmostEqual(
            diagnostics.yearly_metrics[0].mean_actual_excess_return,
            0.02,
        )

    def test_invalid_array_lengths_are_rejected(self) -> None:
        validation = pd.DataFrame(
            {"month_end": ["2024-01-31"], "target": [0.01]}
        )
        with self.assertRaisesRegex(ValueError, "matching lengths"):
            build_validation_diagnostics(
                validation=validation,
                predictions=np.array([0.01, 0.02]),
                probabilities=np.array([0.5]),
                residual_bounds=(-0.1, 0.1),
                target_column="target",
                month_column="month_end",
            )


if __name__ == "__main__":
    unittest.main()
