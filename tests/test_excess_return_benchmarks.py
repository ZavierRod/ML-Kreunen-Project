import unittest

import numpy as np
import pandas as pd

from excess_return_engine.benchmarks import (
    BENCHMARK_VERSION,
    EQUAL_WEIGHT_BENCHMARK_ID,
    relabel_forecast_panels,
)


def panels() -> tuple[pd.DataFrame, pd.DataFrame]:
    training = pd.DataFrame(
        [
            {
                "permno": 1,
                "target_month": "2025-11-30",
                "benchmark_id": "source-benchmark",
                "stock_return_next_month": 0.10,
                "benchmark_return": 0.03,
                "constituent_count": 2,
                "total_lag_market_cap": 300.0,
                "excess_return_next_month": 0.07,
            },
            {
                "permno": 2,
                "target_month": "2025-11-30",
                "benchmark_id": "source-benchmark",
                "stock_return_next_month": -0.02,
                "benchmark_return": 0.03,
                "constituent_count": 2,
                "total_lag_market_cap": 300.0,
                "excess_return_next_month": -0.05,
            },
        ]
    )
    inference = pd.DataFrame(
        [
            {
                "permno": 1,
                "target_month": "2025-12-31",
                "benchmark_id": "source-benchmark",
                "benchmark_return": np.nan,
                "constituent_count": np.nan,
                "total_lag_market_cap": np.nan,
                "excess_return_next_month": np.nan,
            }
        ]
    )
    return training, inference


class BenchmarkTests(unittest.TestCase):
    def test_source_benchmark_is_preserved_by_default(self) -> None:
        training, inference = panels()

        relabeled, current, selection = relabel_forecast_panels(
            training,
            inference,
            None,
        )

        self.assertEqual(selection.version, BENCHMARK_VERSION)
        self.assertEqual(selection.benchmark_id, "source-benchmark")
        self.assertEqual(relabeled["benchmark_return"].iloc[0], 0.03)
        self.assertTrue(current["benchmark_return"].isna().all())

    def test_equal_weight_benchmark_recomputes_labels(self) -> None:
        training, inference = panels()

        relabeled, current, selection = relabel_forecast_panels(
            training,
            inference,
            EQUAL_WEIGHT_BENCHMARK_ID,
        )

        self.assertEqual(
            selection.benchmark_id,
            EQUAL_WEIGHT_BENCHMARK_ID,
        )
        self.assertTrue(
            np.allclose(relabeled["benchmark_return"], 0.04)
        )
        self.assertTrue(
            np.allclose(
                relabeled["excess_return_next_month"],
                (0.06, -0.06),
            )
        )
        self.assertEqual(
            set(current["benchmark_id"]),
            {EQUAL_WEIGHT_BENCHMARK_ID},
        )
        self.assertTrue(current["excess_return_next_month"].isna().all())

    def test_unknown_benchmark_is_rejected(self) -> None:
        training, inference = panels()

        with self.assertRaisesRegex(ValueError, "Unsupported benchmark"):
            relabel_forecast_panels(
                training,
                inference,
                "unknown",
            )


if __name__ == "__main__":
    unittest.main()
