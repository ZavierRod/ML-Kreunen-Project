import unittest

import pandas as pd

from excess_return_engine.universes import (
    ALL_COVERED_UNIVERSE_ID,
    LARGE_LIQUID_UNIVERSE_ID,
    UNIVERSE_VERSION,
    apply_training_universe,
)


def universe_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "permno": 1,
                "month_end": "2025-10-31",
                "market_cap": 100.0,
                "dlyprc": 10.0,
                "n_days": 21,
            },
            {
                "permno": 2,
                "month_end": "2025-10-31",
                "market_cap": 300.0,
                "dlyprc": -20.0,
                "n_days": 21,
            },
            {
                "permno": 3,
                "month_end": "2025-10-31",
                "market_cap": 500.0,
                "dlyprc": 30.0,
                "n_days": 21,
            },
            {
                "permno": 4,
                "month_end": "2025-10-31",
                "market_cap": 900.0,
                "dlyprc": 2.0,
                "n_days": 21,
            },
        ]
    )


class TrainingUniverseTests(unittest.TestCase):
    def test_all_covered_retains_every_row(self) -> None:
        frame = universe_frame()

        retained, selection = apply_training_universe(
            frame,
            ALL_COVERED_UNIVERSE_ID,
        )

        self.assertEqual(selection.version, UNIVERSE_VERSION)
        self.assertEqual(len(retained), 4)
        self.assertEqual(selection.retained_share, 1.0)

    def test_large_liquid_uses_same_month_investability_screen(self) -> None:
        frame = universe_frame()

        retained, selection = apply_training_universe(
            frame,
            LARGE_LIQUID_UNIVERSE_ID,
        )

        self.assertEqual(set(retained["permno"]), {2, 3})
        self.assertEqual(selection.retained_rows, 2)
        self.assertEqual(selection.minimum_monthly_constituents, 2)

    def test_unknown_universe_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "Unsupported training universe",
        ):
            apply_training_universe(universe_frame(), "unknown")


if __name__ == "__main__":
    unittest.main()
