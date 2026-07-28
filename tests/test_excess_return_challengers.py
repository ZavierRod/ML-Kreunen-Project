import unittest

import numpy as np
import pandas as pd

from excess_return_engine.challengers import (
    CHALLENGER_VERSION,
    evaluate_challengers,
)


class ChallengerDiagnosticsTests(unittest.TestCase):
    def test_models_share_one_untouched_evaluation_set(self) -> None:
        rng = np.random.default_rng(5)
        training = pd.DataFrame(
            {
                "size": rng.uniform(-1, 1, 240),
                "momentum_12_1": rng.uniform(-1, 1, 240),
            }
        )
        training["target"] = (
            0.03 * training["size"]
            + 0.08 * training["momentum_12_1"]
            + rng.normal(0, 0.01, len(training))
        )
        validation = pd.DataFrame(
            {
                "size": rng.uniform(-1, 1, 60),
                "momentum_12_1": rng.uniform(-1, 1, 60),
            }
        )
        validation["target"] = (
            0.03 * validation["size"]
            + 0.08 * validation["momentum_12_1"]
            + rng.normal(0, 0.01, len(validation))
        )
        production = np.zeros(len(validation))

        diagnostics = evaluate_challengers(
            training,
            validation,
            ("size", "momentum_12_1"),
            "target",
            production,
            maximum_training_rows=120,
        )

        self.assertEqual(diagnostics.version, CHALLENGER_VERSION)
        self.assertEqual(diagnostics.sampled_training_rows, 120)
        self.assertEqual(diagnostics.evaluation_rows, 60)
        self.assertEqual(
            {item.model_id for item in diagnostics.metrics},
            {
                "zero",
                "elastic_net",
                "ols",
                "random_forest",
                "neural_network",
            },
        )
        self.assertTrue(
            all(item.evaluation_rows == 60 for item in diagnostics.metrics)
        )
        self.assertIn(
            diagnostics.leader_model_id,
            {item.model_id for item in diagnostics.metrics},
        )
        ols = next(
            item for item in diagnostics.metrics if item.model_id == "ols"
        )
        self.assertGreater(ols.oos_r2_vs_zero, 0.8)

    def test_rejects_mismatched_production_predictions(self) -> None:
        frame = pd.DataFrame({"size": [0.0, 1.0], "target": [0.0, 0.1]})

        with self.assertRaisesRegex(ValueError, "match validation rows"):
            evaluate_challengers(
                frame,
                frame,
                ("size",),
                "target",
                np.array([0.0]),
            )


if __name__ == "__main__":
    unittest.main()
