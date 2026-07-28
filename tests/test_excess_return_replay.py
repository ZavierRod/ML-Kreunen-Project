import unittest

import numpy as np
import pandas as pd

from excess_return_engine.benchmarks import EQUAL_WEIGHT_BENCHMARK_ID
from excess_return_engine.replay import (
    REPLAY_VERSION,
    available_as_of_dates,
    build_as_of_snapshot,
    realized_replay_outcome,
)


def replay_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    months = pd.date_range("2020-01-31", periods=5, freq="ME")
    rows = []
    for month_index, month in enumerate(months[:-1]):
        for permno in (1, 2):
            rows.append(
                {
                    "permno": permno,
                    "month_end": month,
                    "target_month": month + pd.offsets.MonthEnd(1),
                    "benchmark_id": "benchmark",
                    "size": permno / 10,
                    "stock_return_next_month": 0.02 * permno,
                    "benchmark_return": 0.01,
                    "constituent_count": 2,
                    "total_lag_market_cap": 100.0,
                    "excess_return_next_month": 0.02 * permno - 0.01,
                    "label_status": "labeled",
                }
            )
    latest = pd.DataFrame(
        [
            {
                "permno": permno,
                "month_end": months[-1],
                "target_month": months[-1] + pd.offsets.MonthEnd(1),
                "benchmark_id": "benchmark",
                "size": permno / 10,
                "stock_return_next_month": np.nan,
                "benchmark_return": np.nan,
                "constituent_count": np.nan,
                "total_lag_market_cap": np.nan,
                "excess_return_next_month": np.nan,
                "label_status": "inference",
            }
            for permno in (1, 2)
        ]
    )
    return pd.DataFrame(rows), latest


class HistoricalReplayTests(unittest.TestCase):
    def test_available_dates_require_prior_history_and_include_latest(self) -> None:
        training, latest = replay_frames()

        dates = available_as_of_dates(
            training,
            latest,
            minimum_history_months=2,
        )

        self.assertEqual(
            tuple(item.date().isoformat() for item in dates),
            ("2020-03-31", "2020-04-30", "2020-05-31"),
        )

    def test_historical_snapshot_hides_every_realized_outcome(self) -> None:
        training, latest = replay_frames()

        snapshot = build_as_of_snapshot(
            training,
            latest,
            "2020-03-15",
        )

        self.assertEqual(snapshot.attrs["replay_version"], REPLAY_VERSION)
        self.assertEqual(snapshot.attrs["snapshot_source"], "historical_replay")
        self.assertEqual(len(snapshot), 2)
        self.assertTrue(snapshot["excess_return_next_month"].isna().all())
        self.assertTrue(snapshot["stock_return_next_month"].isna().all())
        self.assertTrue(snapshot["benchmark_return"].isna().all())
        self.assertTrue(snapshot["constituent_count"].isna().all())
        self.assertTrue(snapshot["total_lag_market_cap"].isna().all())
        self.assertEqual(
            set(snapshot["label_status"]),
            {"historical_replay_outcome_hidden"},
        )

    def test_realized_outcome_is_retrieved_separately(self) -> None:
        training, _ = replay_frames()

        outcome = realized_replay_outcome(training, 2, "2020-03-31")

        self.assertIsNotNone(outcome)
        self.assertEqual(outcome.target_month, "2020-04-30")
        self.assertAlmostEqual(outcome.realized_excess_return, 0.03)
        self.assertEqual(outcome.benchmark_id, "benchmark")

    def test_replay_outcome_uses_selected_benchmark(self) -> None:
        training, _ = replay_frames()

        outcome = realized_replay_outcome(
            training,
            2,
            "2020-03-31",
            EQUAL_WEIGHT_BENCHMARK_ID,
        )

        self.assertEqual(
            outcome.benchmark_id,
            EQUAL_WEIGHT_BENCHMARK_ID,
        )
        self.assertAlmostEqual(outcome.realized_benchmark_return, 0.03)
        self.assertAlmostEqual(outcome.realized_excess_return, 0.01)


if __name__ == "__main__":
    unittest.main()
