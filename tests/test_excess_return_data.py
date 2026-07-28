import tempfile
import unittest
from pathlib import Path

import pandas as pd

from excess_return_engine.data import (
    build_excess_return_panels,
    build_lagged_value_weighted_benchmark,
    resolve_monthly_panel_path,
)


class BenchmarkTests(unittest.TestCase):
    def test_uses_only_exact_prior_month_market_caps(self) -> None:
        stock = pd.DataFrame(
            [
                {"permno": 1, "month_end": "2024-01-31", "ret_m": 0.00, "market_cap": 100},
                {"permno": 1, "month_end": "2024-02-29", "ret_m": 0.10, "market_cap": 110},
                {"permno": 2, "month_end": "2024-01-31", "ret_m": 0.00, "market_cap": 300},
                {"permno": 2, "month_end": "2024-02-29", "ret_m": 0.20, "market_cap": 360},
                {"permno": 3, "month_end": "2024-01-31", "ret_m": 0.00, "market_cap": 500},
                {"permno": 3, "month_end": "2024-03-31", "ret_m": 0.90, "market_cap": 950},
            ]
        )

        benchmark = build_lagged_value_weighted_benchmark(stock)

        self.assertEqual(benchmark["month_end"].dt.strftime("%Y-%m-%d").tolist(), ["2024-02-29"])
        self.assertAlmostEqual(benchmark.iloc[0]["benchmark_return"], 0.175)
        self.assertEqual(benchmark.iloc[0]["constituent_count"], 2)
        self.assertEqual(benchmark.iloc[0]["total_lag_market_cap"], 400)


class LabelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stock = pd.DataFrame(
            [
                {
                    "permno": 1,
                    "month_end": "2024-01-31",
                    "ret_m": 0.01,
                    "market_cap": 100,
                    "momentum": 0.20,
                    "y_next": 0.02,
                },
                {
                    "permno": 1,
                    "month_end": "2024-02-29",
                    "ret_m": 0.03,
                    "market_cap": 105,
                    "momentum": 0.25,
                    "y_next": 0.80,
                },
                {
                    "permno": 1,
                    "month_end": "2024-04-30",
                    "ret_m": 0.80,
                    "market_cap": 189,
                    "momentum": 0.40,
                    "y_next": 0.05,
                },
            ]
        )
        self.benchmark = pd.DataFrame(
            [
                {
                    "month_end": "2024-02-29",
                    "benchmark_id": "test-index",
                    "benchmark_return": 0.01,
                },
                {
                    "month_end": "2024-03-31",
                    "benchmark_id": "test-index",
                    "benchmark_return": -0.02,
                },
                {
                    "month_end": "2024-05-31",
                    "benchmark_id": "test-index",
                    "benchmark_return": 0.04,
                },
            ]
        )

    def test_labels_only_the_exact_next_calendar_month(self) -> None:
        result = build_excess_return_panels(self.stock, self.benchmark)

        self.assertEqual(len(result.training), 1)
        row = result.training.iloc[0]
        self.assertEqual(row["month_end"], pd.Timestamp("2024-01-31"))
        self.assertEqual(row["target_month"], pd.Timestamp("2024-02-29"))
        self.assertAlmostEqual(row["stock_return_next_month"], 0.03)
        self.assertAlmostEqual(row["excess_return_next_month"], 0.02)
        self.assertNotIn("y_next", result.training.columns)

        february = result.unresolved[
            result.unresolved["month_end"] == pd.Timestamp("2024-02-29")
        ].iloc[0]
        self.assertEqual(february["label_status"], "missing_stock_return")
        self.assertTrue(pd.isna(february["stock_return_next_month"]))

    def test_latest_unresolved_rows_become_inference_candidates(self) -> None:
        result = build_excess_return_panels(self.stock, self.benchmark)

        self.assertEqual(len(result.inference), 1)
        self.assertEqual(result.inference.iloc[0]["month_end"], pd.Timestamp("2024-04-30"))
        self.assertEqual(result.inference.iloc[0]["target_month"], pd.Timestamp("2024-05-31"))
        self.assertEqual(result.inference.iloc[0]["label_status"], "missing_stock_return")

    def test_duplicate_security_months_are_rejected(self) -> None:
        duplicate = pd.concat([self.stock, self.stock.iloc[[0]]], ignore_index=True)

        with self.assertRaisesRegex(ValueError, "duplicate security-month"):
            build_excess_return_panels(duplicate, self.benchmark)


class DataPathTests(unittest.TestCase):
    def test_resolves_dataset_root_or_artifacts_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifacts = root / "artifacts"
            artifacts.mkdir()
            expected = artifacts / "monthly_panel.parquet"
            expected.touch()

            self.assertEqual(resolve_monthly_panel_path(root), expected.resolve())
            self.assertEqual(resolve_monthly_panel_path(artifacts), expected.resolve())


if __name__ == "__main__":
    unittest.main()
