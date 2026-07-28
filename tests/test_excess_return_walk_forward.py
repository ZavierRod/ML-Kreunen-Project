import unittest

import numpy as np
import pandas as pd

from excess_return_engine.walk_forward import (
    WALK_FORWARD_VERSION,
    evaluate_walk_forward,
)


def walk_forward_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(17)
    months = pd.date_range("2018-01-31", periods=18, freq="ME")
    rows = []
    for month_index, month in enumerate(months):
        for permno in range(1, 7):
            factor = (permno - 3.5) / 3.5 + month_index / 100
            rows.append(
                {
                    "permno": permno,
                    "month_end": month,
                    "target_month": month + pd.offsets.MonthEnd(1),
                    "size": factor,
                    "excess_return_next_month": (
                        0.03 * factor + rng.normal(0, 0.005)
                    ),
                }
            )
    historical = pd.DataFrame(rows)
    calibration = historical[
        historical["month_end"].isin(months[-8:-4])
    ].copy()
    calibration["_prediction"] = 0.02 * calibration["size"]
    return historical, calibration


class WalkForwardTests(unittest.TestCase):
    def test_predictions_use_only_earlier_months(self) -> None:
        historical, calibration = walk_forward_frames()

        evaluation = evaluate_walk_forward(
            historical=historical,
            calibration_residual_frame=calibration,
            selected_factors=("size",),
            target_column="excess_return_next_month",
            month_column="month_end",
            alpha=0.0001,
            l1_ratio=0.5,
            interval_level=0.8,
            target_clip_quantiles=(0.001, 0.999),
            evaluation_month_count=4,
        )

        diagnostics = evaluation.diagnostics
        predictions = evaluation.predictions
        self.assertEqual(diagnostics.version, WALK_FORWARD_VERSION)
        self.assertEqual(diagnostics.evaluation_months, 4)
        self.assertEqual(diagnostics.evaluation_rows, 24)
        self.assertEqual(diagnostics.calibration_residual_rows, 24)
        self.assertEqual(
            set(predictions["split"]),
            {"calibration_residual", "walk_forward_evaluation"},
        )
        evaluation_rows = predictions[
            predictions["split"] == "walk_forward_evaluation"
        ]
        self.assertTrue(
            (
                predictions["training_end"]
                < predictions["as_of_date"]
            ).all()
        )
        self.assertTrue(
            (
                evaluation_rows["target_month"]
                == evaluation_rows["as_of_date"]
                + pd.offsets.MonthEnd(1)
            ).all()
        )
        self.assertTrue(
            evaluation_rows["probability_positive"].between(0, 1).all()
        )

    def test_later_month_refit_includes_prior_evaluation_outcomes(self) -> None:
        historical, calibration = walk_forward_frames()

        evaluation = evaluate_walk_forward(
            historical=historical,
            calibration_residual_frame=calibration,
            selected_factors=("size",),
            target_column="excess_return_next_month",
            month_column="month_end",
            alpha=0.0001,
            l1_ratio=0.5,
            interval_level=0.8,
            target_clip_quantiles=(0.001, 0.999),
            evaluation_month_count=4,
        )

        monthly = evaluation.diagnostics.monthly_metrics
        self.assertEqual(len(monthly), 4)
        self.assertGreater(
            monthly[-1].training_rows,
            monthly[0].training_rows,
        )
        self.assertTrue(
            all(item.rank_ic is not None for item in monthly)
        )

    def test_rejects_non_calendar_target_month(self) -> None:
        historical, calibration = walk_forward_frames()
        historical.loc[
            historical["month_end"] == historical["month_end"].max(),
            "target_month",
        ] += pd.offsets.MonthEnd(1)

        with self.assertRaisesRegex(ValueError, "exact next target month"):
            evaluate_walk_forward(
                historical=historical,
                calibration_residual_frame=calibration,
                selected_factors=("size",),
                target_column="excess_return_next_month",
                month_column="month_end",
                alpha=0.0001,
                l1_ratio=0.5,
                interval_level=0.8,
                target_clip_quantiles=(0.001, 0.999),
                evaluation_month_count=4,
            )

    def test_current_and_future_outcomes_do_not_change_predictions(self) -> None:
        historical, calibration = walk_forward_frames()
        modified = historical.copy()
        modified.loc[
            modified["month_end"] == modified["month_end"].max(),
            "excess_return_next_month",
        ] += 1.0
        arguments = {
            "calibration_residual_frame": calibration,
            "selected_factors": ("size",),
            "target_column": "excess_return_next_month",
            "month_column": "month_end",
            "alpha": 0.0001,
            "l1_ratio": 0.5,
            "interval_level": 0.8,
            "target_clip_quantiles": (0.001, 0.999),
            "evaluation_month_count": 4,
        }

        original = evaluate_walk_forward(
            historical=historical,
            **arguments,
        ).predictions
        changed = evaluate_walk_forward(
            historical=modified,
            **arguments,
        ).predictions
        columns = [
            "predicted_excess_return",
            "probability_positive",
            "interval_lower",
            "interval_upper",
        ]
        original_evaluation = original[
            original["split"] == "walk_forward_evaluation"
        ]
        changed_evaluation = changed[
            changed["split"] == "walk_forward_evaluation"
        ]

        pd.testing.assert_frame_equal(
            original_evaluation[columns].reset_index(drop=True),
            changed_evaluation[columns].reset_index(drop=True),
        )

    def test_rejects_calibration_residuals_from_evaluation_period(self) -> None:
        historical, calibration = walk_forward_frames()
        leaked = calibration.copy()
        leaked["month_end"] = historical["month_end"].max()
        leaked["target_month"] = (
            leaked["month_end"] + pd.offsets.MonthEnd(1)
        )

        with self.assertRaisesRegex(
            ValueError,
            "must precede every evaluation month",
        ):
            evaluate_walk_forward(
                historical=historical,
                calibration_residual_frame=leaked,
                selected_factors=("size",),
                target_column="excess_return_next_month",
                month_column="month_end",
                alpha=0.0001,
                l1_ratio=0.5,
                interval_level=0.8,
                target_clip_quantiles=(0.001, 0.999),
                evaluation_month_count=4,
            )


if __name__ == "__main__":
    unittest.main()
