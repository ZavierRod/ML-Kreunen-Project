import unittest

import pandas as pd

from ui.factor_explorer.engine import detail_table
from ui.factor_explorer.metrics import normalize_metric_selection, picker_option_label


class DetailTableTests(unittest.TestCase):
    def test_detail_table_contains_only_observed_periods(self) -> None:
        panel = pd.DataFrame(
            [
                {
                    "from_year": 2022,
                    "to_year": 2023,
                    "period": "2022-2023",
                    "metric": "Revenue",
                    "pct_change": 0.10,
                    "weight": 0.40,
                },
                {
                    "from_year": 2022,
                    "to_year": 2023,
                    "period": "2022-2023",
                    "metric": "EPS",
                    "pct_change": 0.15,
                    "weight": 0.60,
                },
                {
                    "from_year": 2023,
                    "to_year": 2024,
                    "period": "2023-2024",
                    "metric": "Revenue",
                    "pct_change": 0.20,
                    "weight": 0.25,
                },
                {
                    "from_year": 2023,
                    "to_year": 2024,
                    "period": "2023-2024",
                    "metric": "EPS",
                    "pct_change": -0.60,
                    "weight": 0.75,
                },
            ]
        )

        detail = detail_table(panel, ["Revenue", "EPS"])

        self.assertEqual(detail["period"].tolist(), ["2022-2023", "2023-2024"])
        self.assertEqual(len(detail), panel["period"].nunique())
        self.assertEqual(detail["Revenue pct"].tolist(), [0.10, 0.20])
        self.assertEqual(detail["EPS weight"].tolist(), [0.60, 0.75])


class PickerOptionLabelTests(unittest.TestCase):
    def test_standalone_metric_is_labeled_weight_ready(self) -> None:
        self.assertEqual(
            picker_option_label("Revenue", []),
            "● Revenue — Weight-ready",
        )

    def test_derived_metric_warns_about_selected_parent(self) -> None:
        label = picker_option_label("EV", ["Price", "NetCash"])

        self.assertEqual(
            label,
            "⚠ EV — Rank-only; overlaps NetCash, Price",
        )

    def test_parent_warns_about_selected_derived_metric(self) -> None:
        label = picker_option_label("Price", ["EV"])

        self.assertEqual(
            label,
            "⚠ Price — Weight-ready; overlaps EV",
        )

    def test_formatted_widget_values_are_normalized(self) -> None:
        self.assertEqual(
            normalize_metric_selection(
                [
                    "● Shares — Weight-ready",
                    "⚠ EV — Rank-only; overlaps Price",
                ]
            ),
            ["Shares", "EV"],
        )

    def test_formatted_selected_value_does_not_break_option_label(self) -> None:
        self.assertEqual(
            picker_option_label("EV", ["● Shares — Weight-ready"]),
            "⚠ EV — Rank-only; overlaps Shares",
        )


if __name__ == "__main__":
    unittest.main()
